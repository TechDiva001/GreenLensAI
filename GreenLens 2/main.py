import os
import uuid
import time
import json
import logging
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import UPLOAD_DIR
from services.vision_service import analyze_report_image
from services.weather_service import get_weather_forecast
from services.geospatial_service import find_nearest_drain_segment, detect_waste_hotspots
from services.risk_service import calculate_flood_risk_v2, predict_maintenance_window
from services.dispatch_service import generate_dispatch_recommendation, prioritize_incidents
from services.optimization_service import optimize_cleanup_route
from services.verification_service import calculate_image_hash, check_for_duplicate_or_fraud, verify_cleanup
from services.assistant_service import generate_daily_summary, chat_municipal_assistant

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GreenLensAI_V2")

app = FastAPI(
    title="GreenLens AI Advanced Backend (V2)",
    description="Comprehensive AI Backend Services (all 25 AI functions and 7 workstreams)",
    version="2.0.0"
)

# Enable CORS for phone Wi-Fi connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local JSON DB for GreenLens 2
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

def load_db() -> List[dict]:
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading local DB: {e}")
        return []

def save_db(data: List[dict]):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving to local DB: {e}")

class ChatQuery(BaseModel):
    query: str

class OptimizationRequest(BaseModel):
    depot_latitude: float = 5.6037
    depot_longitude: float = -0.1870
    truck_capacity_kg: float = 1000.0

@app.get("/api/health")
def health_check():
    from config import GEMINI_API_KEY
    return {
        "status": "healthy",
        "version": "2.0.0",
        "vision_engine": "Gemini 2.5/1.5 Flash (Cloud)" if GEMINI_API_KEY else "Local YOLOv8 + OpenCV (Offline Fallback)",
        "weather_engine": "Open-Meteo (Free, No Key)",
        "optimization_engine": "Local greedy TSP",
        "assistant_engine": "Gemini RAG" if GEMINI_API_KEY else "Keyword Heuristic Fallback"
    }

@app.post("/api/ai/analyze-image")
async def analyze_image(
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    historical_flooding: bool = Form(False),
    description: Optional[str] = Form("")
):
    """
    Main ingestion endpoint:
    - Runs duplicate & fraud checks
    - Image quality & validity
    - Gutter/drain and waste detection
    - Geospatial proximity
    - Weather forecast & flood risk scoring
    - Predictive maintenance window
    - Dispatch prioritization
    """
    try:
        report_id = f"GL-{uuid.uuid4().hex[:6].upper()}"
        
        # Save image
        file_ext = os.path.splitext(image.filename)[1] or ".jpg"
        image_name = f"{report_id}_before{file_ext}"
        image_path = os.path.join(UPLOAD_DIR, image_name)
        
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
            
        # Calculate image perceptual hash for deduplication
        img_hash = calculate_image_hash(image_path)
        
        # Run duplicate / fraud check
        db_entries = load_db()
        current_time = time.time()
        
        dup_check = check_for_duplicate_or_fraud(
            new_hash=img_hash,
            new_lat=latitude,
            new_lon=longitude,
            new_timestamp=current_time,
            existing_reports=db_entries
        )
        
        if dup_check.get("status") == "DUPLICATE":
            return {
                "status": "DUPLICATE",
                "message": dup_check.get("message"),
                "report_id": dup_check.get("duplicate_of_id")
            }
            
        # Analyze image
        vision_res = analyze_report_image(image_path)
        
        # Fetch weather rain forecast
        weather_res = get_weather_forecast(latitude, longitude)
        
        # Proximity to known drains
        geospatial_res = find_nearest_drain_segment(latitude, longitude)
        
        # Count recurring reports near this coordinate (mock accumulation)
        accumulation_count = sum(
            1 for r in db_entries 
            if r.get("nearest_segment_id") == geospatial_res.get("nearest_segment_id")
        )
        
        # Calculate Flood Risk Score (V2)
        risk_res = calculate_flood_risk_v2(
            blockage_percentage=float(vision_res.get("blockage_percentage", 0)),
            rain_forecast_mm=weather_res.get("rain_24h_mm", 0.0),
            historical_flooding=historical_flooding,
            capacity_restored=geospatial_res.get("capacity_restored", 100),
            accumulation_count=accumulation_count,
            proximity_level=geospatial_res.get("proximity_level", "LOW")
        )
        
        # Calculate Predictive Maintenance
        maintenance_res = predict_maintenance_window(
            blockage_percentage=float(vision_res.get("blockage_percentage", 0)),
            accumulation_count=accumulation_count,
            historical_flooding=historical_flooding
        )
        
        # Build report
        report_entry = {
            "report_id": report_id,
            "image_path": image_path,
            "image_hash": img_hash,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current_time,
            "description": description,
            "historical_flooding": historical_flooding,
            "status": "Submitted" if dup_check.get("status") == "OK" else "Under Verification",
            "fraud_flag": dup_check.get("status") == "FRAUD_SUSPECTED",
            "fraud_reason": dup_check.get("reason", ""),
            
            # Vision output
            "waste_detected": vision_res.get("waste_detected", False),
            "waste_type": vision_res.get("waste_type", "none"),
            "estimated_waste_coverage": vision_res.get("estimated_waste_coverage", 0),
            "waste_density": vision_res.get("waste_density", "none"),
            "waste_inside_drain": vision_res.get("waste_inside_drain", False),
            "waste_beside_drain": vision_res.get("waste_beside_drain", False),
            "drain_detected": vision_res.get("drain_detected", False),
            "drainage_structure": vision_res.get("drainage_structure", "none"),
            "blockage_percentage": vision_res.get("blockage_percentage", 0),
            "opening_obstruction": vision_res.get("opening_obstruction", 0),
            "water_flow_obstruction": vision_res.get("water_flow_obstruction", 0),
            "sediment_accumulation": vision_res.get("sediment_accumulation", 0),
            "vegetation_obstruction": vision_res.get("vegetation_obstruction", 0),
            
            # Quality output
            "is_screenshot": vision_res.get("is_screenshot", False),
            "is_irrelevant": vision_res.get("is_irrelevant", False),
            "is_manipulated": vision_res.get("is_manipulated", False),
            "quality_score": vision_res.get("quality_score", 90),
            "usable": vision_res.get("usable", True),
            "confidence": vision_res.get("confidence", 0.90),
            "bounding_boxes": vision_res.get("bounding_boxes", []),
            
            # Weather output
            "rain_24h_mm": weather_res.get("rain_24h_mm", 0.0),
            "rain_48h_mm": weather_res.get("rain_48h_mm", 0.0),
            "rain_probability_24h": weather_res.get("rain_probability_24h", 0),
            "rain_probability_48h": weather_res.get("rain_probability_48h", 0),
            
            # Geospatial output
            "nearest_segment_id": geospatial_res.get("nearest_segment_id"),
            "nearest_segment_name": geospatial_res.get("segment_name"),
            "proximity_distance_meters": geospatial_res.get("distance_meters"),
            "proximity_level": geospatial_res.get("proximity_level"),
            
            # Risk output
            "risk_score": risk_res.get("risk_score", 0.0),
            "risk_level": risk_res.get("risk_level", "LOW"),
            "risk_contributions": risk_res.get("contributions"),
            
            # Maintenance output
            "days_until_critical": maintenance_res.get("days_until_critical"),
            "maintenance_required": maintenance_res.get("maintenance_required"),
            "maintenance_message": maintenance_res.get("prediction_message")
        }
        
        # Dispatch Recommendation
        dispatch_res = generate_dispatch_recommendation(report_entry)
        report_entry["dispatch_recommendation"] = dispatch_res
        
        # Save to DB
        db_entries.append(report_entry)
        save_db(db_entries)
        
        return report_entry
    except Exception as e:
        logger.exception("Error in analyze-image API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.post("/api/ai/verify-cleanup")
async def verify_report_cleanup(
    report_id: str = Form(...),
    after_image: UploadFile = File(...)
):
    db_entries = load_db()
    
    original_report = None
    original_idx = -1
    for i, report in enumerate(db_entries):
        if report.get("report_id") == report_id:
            original_report = report
            original_idx = i
            break
            
    if not original_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found."
        )
        
    try:
        # Save after image
        file_ext = os.path.splitext(after_image.filename)[1] or ".jpg"
        after_image_name = f"{report_id}_after{file_ext}"
        after_image_path = os.path.join(UPLOAD_DIR, after_image_name)
        
        with open(after_image_path, "wb") as buffer:
            buffer.write(await after_image.read())
            
        before_image_path = original_report["image_path"]
        
        # Verify
        verify_res = verify_cleanup(before_image_path, after_image_path)
        
        db_entries[original_idx]["after_image_path"] = after_image_path
        db_entries[original_idx]["cleanup_verified"] = verify_res.get("cleanup_verified", False)
        db_entries[original_idx]["before_blockage_verified"] = verify_res.get("before_blockage", 0)
        db_entries[original_idx]["after_blockage_verified"] = verify_res.get("after_blockage", 0)
        db_entries[original_idx]["improvement_percentage"] = verify_res.get("estimated_improvement", 0)
        db_entries[original_idx]["verification_explanation"] = verify_res.get("explanation", "")
        
        if verify_res.get("cleanup_verified", False):
            db_entries[original_idx]["status"] = "Resolved"
        else:
            db_entries[original_idx]["status"] = "Verification Failed"
            
        save_db(db_entries)
        
        return {
            "report_id": report_id,
            "status": db_entries[original_idx]["status"],
            "verification_result": verify_res
        }
    except Exception as e:
        logger.exception("Error in verify-cleanup API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/api/ai/prioritized")
def get_prioritized_reports():
    db_entries = load_db()
    active_incidents = [r for r in db_entries if r.get("status") != "DUPLICATE"]
    return prioritize_incidents(active_incidents)

@app.get("/api/ai/hotspots")
def get_waste_hotspots():
    """
    Identifies clusters of waste reports to locate hotspots (AI Function #17).
    """
    db_entries = load_db()
    active_incidents = [r for r in db_entries if r.get("status") != "DUPLICATE" and r.get("waste_detected", False)]
    return detect_waste_hotspots(active_incidents)

@app.post("/api/ai/route-optimization")
def get_optimized_route(req: OptimizationRequest):
    """
    Solves route optimization (TSP) for cleanups and outputs CO2/fuel savings (AI Function #19 & #20).
    """
    db_entries = load_db()
    active_incidents = [
        r for r in db_entries 
        if r.get("status") in ["Submitted", "Under Verification"] and r.get("waste_detected", False)
    ]
    return optimize_cleanup_route(
        incidents=active_incidents,
        depot_lat=req.depot_latitude,
        depot_lon=req.depot_longitude,
        truck_capacity=req.truck_capacity_kg
    )

@app.post("/api/ai/assistant/chat")
def ask_assistant(req: ChatQuery):
    """
    Conversational municipal assistant RAG bot (AI Function #21).
    """
    db_entries = load_db()
    return {"response": chat_municipal_assistant(req.query, db_entries)}

@app.get("/api/ai/assistant/daily-summary")
def get_daily_summary_report():
    """
    Generates summary report text of all operational data (AI Function #22).
    """
    db_entries = load_db()
    summary_text = generate_daily_summary(db_entries)
    return {"summary": summary_text}
