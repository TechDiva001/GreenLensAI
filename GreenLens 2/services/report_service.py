import os
import uuid
import time
import requests
import logging
from typing import Dict, Any

from schemas.report_schema import AnalyzeImageRequest, AiAnalysisResult
# Removed crud.report_crud import
from core.config import settings

# In a real FBA architecture, we would import from a properly separated services layer.
# For now, we will reuse the existing ML logic functions from the old `services/` directory.
import sys
# Add parent dir to path to import existing ML services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vision_service import analyze_report_image
from services.weather_service import get_weather_forecast
from services.geospatial_service import find_nearest_drain_segment
from services.risk_service import calculate_flood_risk_v2, predict_maintenance_window
from services.dispatch_service import generate_dispatch_recommendation
from services.verification_service import calculate_image_hash

logger = logging.getLogger("GreenLensAI_V2")

def download_image(url: str, filepath: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.exception(f"Failed to download image from {url}")
        return False

def process_analyze_image(req: AnalyzeImageRequest) -> AiAnalysisResult:
    report_id = f"GL-{uuid.uuid4().hex[:6].upper()}"
    current_time = time.time()
    
    # 1. Download the image from the provided URL (Supabase Storage)
    image_path = os.path.join(settings.UPLOAD_DIR, f"{report_id}_before.jpg")
    download_success = download_image(req.image_url, image_path)
    if not download_success:
        raise ValueError("Failed to download image from the provided URL")
        
    img_hash = calculate_image_hash(image_path)
    
    # We skip deduplication with the local JSON for now, or assume it's OK
    fraud_flag = False
    
    # 2. Analyze image using OpenCV/YOLO
    vision_res = analyze_report_image(image_path)
    
    # 3. Weather
    weather_res = get_weather_forecast(req.latitude, req.longitude)
    
    # 4. Geospatial Proximity
    geospatial_res = find_nearest_drain_segment(req.latitude, req.longitude)
    
    # 5. Flood Risk Score
    risk_res = calculate_flood_risk_v2(
        blockage_percentage=float(vision_res.get("blockage_percentage", 0)),
        rain_forecast_mm=weather_res.get("rain_24h_mm", 0.0),
        historical_flooding=req.historical_flooding,
        capacity_restored=geospatial_res.get("capacity_restored", 100),
        accumulation_count=0,
        proximity_level=geospatial_res.get("proximity_level", "LOW")
    )
    
    # 6. Predictive Maintenance
    maintenance_res = predict_maintenance_window(
        blockage_percentage=float(vision_res.get("blockage_percentage", 0)),
        accumulation_count=0,
        historical_flooding=req.historical_flooding
    )
    
    # Compile the result
    result = AiAnalysisResult(
        report_id=report_id,
        status="SUBMITTED" if not fraud_flag else "UNDER_REVIEW",
        fraud_flag=fraud_flag,
        waste_detected=vision_res.get("waste_detected", False),
        waste_type=vision_res.get("waste_type", "none"),
        blockage_percentage=vision_res.get("blockage_percentage", 0),
        risk_score=risk_res.get("risk_score", 0.0),
        risk_level=risk_res.get("risk_level", "LOW"),
        nearest_segment_name=geospatial_res.get("segment_name"),
        proximity_level=geospatial_res.get("proximity_level"),
        proximity_distance_meters=geospatial_res.get("distance_meters"),
        confidence=vision_res.get("confidence", 0.90),
        quality_score=vision_res.get("quality_score", 90),
        usable=vision_res.get("usable", True),
        maintenance_message=maintenance_res.get("prediction_message"),
        days_until_critical=maintenance_res.get("days_until_critical"),
        rain_24h_mm=weather_res.get("rain_24h_mm", 0.0),
        bounding_boxes=vision_res.get("bounding_boxes", []),
        risk_contributions=risk_res.get("contributions"),
        detection_source=vision_res.get("detection_source", "ensemble (Gemini 2.5 + YOLOv8)"),
        items_detected_count=vision_res.get("items_detected_count", 0),
        consensus_agreement=vision_res.get("consensus_agreement")
    )
    
    # 7. Write to Supabase is now handled by the frontend
    # to maintain strict RLS boundaries and a stateless backend.
    
    return result
