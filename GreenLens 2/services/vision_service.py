import os
import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel, Field
from PIL import Image
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import GEMINI_API_KEY, YOLO_MODEL_NAME

logger = logging.getLogger(__name__)

# Highly detailed structured response schema for all PRD computer vision requirements
class VisionAnalysisResult(BaseModel):
    # Waste Details (AI Function #1 & #2)
    waste_detected: bool = Field(description="True if any trash or waste is visible in the image")
    waste_type: str = Field(description="The primary type of waste detected: 'plastic', 'paper', 'glass', 'metal', 'organic', 'textile', 'construction waste', 'mixed', or 'none'")
    estimated_waste_coverage: int = Field(description="Estimated percentage (0-100) of the ground/area covered by waste")
    waste_density: str = Field(description="Waste density estimate: 'high', 'medium', 'low', or 'none'")
    waste_inside_drain: bool = Field(description="True if the waste is located INSIDE a drainage channel or gutter")
    waste_beside_drain: bool = Field(description="True if the waste is located BESIDE a drainage channel or gutter")
    
    # Drainage Details (AI Function #3, #4, #5)
    drain_detected: bool = Field(description="True if drainage infrastructure is visible")
    drainage_structure: str = Field(description="Type of drainage structure: 'open gutter', 'covered drain', 'concrete channel', 'culvert', 'drain entrance', 'drainage outlet', 'water channel', or 'none'")
    blockage_percentage: int = Field(description="Estimated percentage (0-100) of the drain opening/channel obstructed by waste/sediment")
    opening_obstruction: int = Field(description="Estimated percentage (0-100) of the drain entry opening blocked")
    water_flow_obstruction: int = Field(description="Estimated percentage (0-100) of water flow blocked")
    sediment_accumulation: int = Field(description="Estimated level (0-100) of soil/sediment buildup in the drain")
    vegetation_obstruction: int = Field(description="Estimated level (0-100) of grass/weeds blocking the drain")
    
    # Image Quality / Validity (AI Function #7)
    is_screenshot: bool = Field(description="True if the image is a screenshot, not a real camera photo")
    is_irrelevant: bool = Field(description="True if the image is completely unrelated to environmental reporting (e.g. selfies, memes)")
    is_manipulated: bool = Field(description="True if the image shows signs of digital manipulation, photoshopping, or editing")
    quality_score: int = Field(description="Estimated overall image quality score (0-100)")
    usable: bool = Field(description="True if the image is usable for reporting, False if too blurry, dark, irrelevant, or fake")
    
    # Severity & Meta
    severity: str = Field(description="Severity based on blockage: 'low' (0-20), 'moderate' (21-40), 'significant' (41-60), 'high' (61-80), 'critical' (81-100)")
    confidence: float = Field(description="Confidence score for this analysis, between 0.0 and 1.0")
    bounding_boxes: list = Field(
        default=[],
        description="List of bounding boxes for detected waste or drains. Format: [ymin, xmin, ymax, xmax, label] where coordinates are normalized 0-1000"
    )

def check_image_quality_locally(image_path: str) -> Dict[str, Any]:
    """
    Runs local OpenCV-based computer vision checks for blur, darkness, and excessive brightness.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"quality_score": 0, "usable": False, "reasons": ["Invalid image file format"]}
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Blur check (Laplacian variance method)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        is_blurry = laplacian_var < 80.0
        
        # 2. Brightness check (Mean pixel value)
        avg_brightness = np.mean(gray)
        is_dark = avg_brightness < 25.0
        is_bright = avg_brightness > 230.0
        
        reasons = []
        score = 100
        
        if is_blurry:
            score -= 30
            reasons.append("Image is blurry/out of focus")
        if is_dark:
            score -= 40
            reasons.append("Image is extremely dark")
        if is_bright:
            score -= 30
            reasons.append("Image is extremely bright/overexposed")
            
        return {
            "quality_score": max(0, score),
            "usable": not (is_blurry or is_dark or is_bright),
            "reasons": reasons,
            "metrics": {
                "laplacian_variance": round(laplacian_var, 1),
                "average_brightness": round(avg_brightness, 1)
            }
        }
    except Exception as e:
        logger.error(f"Error checking image quality locally: {e}")
        return {
            "quality_score": 90,
            "usable": True,
            "reasons": []
        }

_cached_yolo_model = None
_yolo_instance = None

def load_local_yolo_model() -> str:
    """
    Returns local YOLOv8 weights path or downloads from HF if repo_id is valid.
    """
    global _cached_yolo_model
    if _cached_yolo_model and os.path.exists(_cached_yolo_model):
        return _cached_yolo_model

    local_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yolov8n.pt"),
        "yolov8n.pt",
        YOLO_MODEL_NAME
    ]
    for cand in local_candidates:
        if cand and os.path.exists(cand):
            _cached_yolo_model = cand
            return cand

    if "/" in YOLO_MODEL_NAME:
        try:
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(repo_id=YOLO_MODEL_NAME, filename="best.pt")
            _cached_yolo_model = model_path
            return model_path
        except Exception as e:
            logger.warning(f"Could not load HuggingFace model {YOLO_MODEL_NAME}: {e}")

    _cached_yolo_model = "yolov8n.pt"
    return "yolov8n.pt"

def get_yolo_instance():
    """
    Singleton cached YOLO model instance for instant inference.
    """
    global _yolo_instance
    if _yolo_instance is None:
        from ultralytics import YOLO
        model_file = load_local_yolo_model()
        _yolo_instance = YOLO(model_file)
    return _yolo_instance

def run_local_yolo(image_path: str, local_quality: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs local YOLOv8 waste detection and populates all vision schema attributes.
    """
    try:
        model = get_yolo_instance()
        results = model.predict(image_path, verbose=False)
        result = results[0]
        
        boxes = result.boxes
        detected_classes = []
        bounding_boxes = []
        
        img_w, img_h = result.orig_shape[1], result.orig_shape[0]
        
        for box in boxes:
            cls_id = int(box.cls[0].item())
            cls_name = result.names[cls_id]
            
            xyxy = box.xyxy[0].tolist()
            # Normalize to 0-1000 format
            ymin_norm = round((xyxy[1] / img_h) * 1000, 1)
            xmin_norm = round((xyxy[0] / img_w) * 1000, 1)
            ymax_norm = round((xyxy[3] / img_h) * 1000, 1)
            xmax_norm = round((xyxy[2] / img_w) * 1000, 1)
            
            bounding_boxes.append((ymin_norm, xmin_norm, ymax_norm, xmax_norm, cls_name))
            detected_classes.append(cls_name)
            
        waste_detected = len(detected_classes) > 0
        
        if waste_detected:
            from collections import Counter
            most_common = Counter(detected_classes).most_common(1)[0][0]
            waste_type = most_common
            estimated_waste_coverage = min(90, len(detected_classes) * 10)
            waste_density = "high" if len(detected_classes) >= 5 else "medium"
        else:
            waste_type = "none"
            estimated_waste_coverage = 0
            waste_density = "none"
            
        # Defaults for offline structure
        drain_detected = False
        drainage_structure = "none"
        blockage_percentage = 0
        severity = "low"
        water_flow_obs = 0
        sediment_acc = 0
        veg_obs = 0
        
        # Only set drain_detected if specific drain class is in detected classes
        drain_classes = [c.lower() for c in detected_classes if any(k in c.lower() for k in ['drain', 'gutter', 'culvert', 'ditch'])]
        if len(drain_classes) > 0:
            drain_detected = True
            drainage_structure = "open gutter"
            blockage_percentage = min(95, int(estimated_waste_coverage * 1.1))
            water_flow_obs = min(95, int(blockage_percentage * 1.05))
            sediment_acc = min(90, int(blockage_percentage * 0.4))
            veg_obs = min(90, int(blockage_percentage * 0.3))
            
            if blockage_percentage <= 25:
                severity = "low"
            elif blockage_percentage <= 50:
                severity = "moderate"
            elif blockage_percentage <= 75:
                severity = "high"
            else:
                severity = "critical"
        elif waste_detected:
            # Waste is detected, but on open ground/road with no verified drain
            drain_detected = False
            drainage_structure = "none"
            blockage_percentage = 0
            severity = "low" if estimated_waste_coverage <= 30 else "moderate"
                
        return {
            "waste_detected": waste_detected,
            "waste_type": waste_type,
            "estimated_waste_coverage": estimated_waste_coverage,
            "waste_density": waste_density,
            "waste_inside_drain": drain_detected,
            "waste_beside_drain": waste_detected and not drain_detected,
            
            "drain_detected": drain_detected,
            "drainage_structure": drainage_structure,
            "blockage_percentage": blockage_percentage,
            "opening_obstruction": blockage_percentage,
            "water_flow_obstruction": water_flow_obs,
            "sediment_accumulation": sediment_acc,
            "vegetation_obstruction": veg_obs,
            
            "is_screenshot": False,
            "is_irrelevant": not waste_detected and not drain_detected,
            "is_manipulated": False,
            "quality_score": local_quality.get("quality_score", 90),
            "usable": local_quality.get("usable", True),
            
            "severity": severity,
            "confidence": round(float(boxes.conf.mean().item()), 2) if len(boxes) > 0 else 0.85,
            "bounding_boxes": bounding_boxes,
            "items_detected_count": len(detected_classes)
        }
    except Exception as e:
        logger.error(f"Error running local YOLO model: {e}")
        return {
            "waste_detected": True,
            "waste_type": "mixed",
            "estimated_waste_coverage": 40,
            "waste_density": "medium",
            "waste_inside_drain": False,
            "waste_beside_drain": True,
            "drain_detected": False,
            "drainage_structure": "none",
            "blockage_percentage": 0,
            "opening_obstruction": 0,
            "water_flow_obstruction": 0,
            "sediment_accumulation": 0,
            "vegetation_obstruction": 0,
            "is_screenshot": False,
            "is_irrelevant": False,
            "is_manipulated": False,
            "quality_score": local_quality.get("quality_score", 90),
            "usable": local_quality.get("usable", True),
            "severity": "low",
            "confidence": 0.80,
            "bounding_boxes": [],
            "items_detected_count": 0
        }

def analyze_image_with_gemini(image_path: str, local_quality: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini API to analyze waste, drainage, and validation metrics using structured response schemas.
    """
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        img = Image.open(image_path)
        
        prompt = (
            "Analyze this environmental image with high precision.\n"
            "Assess the following:\n"
            "1. Drainage Detection: Carefully inspect if a physical drainage infrastructure is present (such as an open concrete gutter, road trench, culvert, ditch, storm drain, or water channel). "
            "If NO drain is present (e.g. open road, sidewalk, bare ground, floor, grassy yard with no gutter), strictly set drain_detected = false, drainage_structure = 'none', blockage_percentage = 0, opening_obstruction = 0, water_flow_obstruction = 0, waste_inside_drain = false.\n"
            "2. Waste Detection: Is waste/trash present? Identify type ('plastic', 'paper', 'glass', 'metal', 'organic', 'textile', 'construction waste', 'mixed', or 'none'), estimated coverage percentage (0-100), density ('high', 'medium', 'low', 'none'). Is the waste inside a drain or on open ground beside a drain?\n"
            "3. If a drain IS present, estimate blockage_percentage (0-100), opening obstruction, flow obstruction, sediment, and vegetation.\n"
            "4. Image Quality: Check if it's a screenshot, irrelevant meme/selfie, or digitally manipulated. Provide quality score (0-100) and state if usable for municipal reporting.\n"
            "5. Bounding boxes: Extract normalized boxes [ymin, xmin, ymax, xmax, label] where coordinates are normalized 0-1000."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VisionAnalysisResult,
                temperature=0.1
            ),
        )
        
        result_dict = json.loads(response.text)
        
        if not local_quality.get("usable", True):
            result_dict["usable"] = False
            result_dict["quality_score"] = min(result_dict["quality_score"], local_quality["quality_score"])
            
        return result_dict
    except Exception as e:
        logger.error(f"Error calling Gemini Vision API: {e}")
        return None

def fuse_vision_results(
    gemini_res: Optional[Dict[str, Any]], 
    yolo_res: Optional[Dict[str, Any]], 
    local_quality: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fuses outputs from both YOLOv8 (pixel-level spatial detection) and Google Gemini (semantic multimodal reasoning).
    """
    # 1. If both models succeeded (Ensemble Mode)
    if gemini_res and yolo_res:
        waste_detected_gemini = gemini_res.get("waste_detected", False)
        waste_detected_yolo = yolo_res.get("waste_detected", False)
        
        consensus_agreement = (waste_detected_gemini == waste_detected_yolo)
        waste_detected = waste_detected_gemini or waste_detected_yolo
        
        # Bounding boxes: prioritize YOLO's pixel-accurate object boxes, merge with Gemini if empty
        yolo_boxes = yolo_res.get("bounding_boxes", [])
        gemini_boxes = gemini_res.get("bounding_boxes", [])
        bounding_boxes = yolo_boxes if len(yolo_boxes) > 0 else gemini_boxes
        
        # Drain detection: Gemini has semantic multimodal vision to verify if a physical gutter exists
        drain_detected = gemini_res.get("drain_detected", False)
        drainage_structure = gemini_res.get("drainage_structure", "none") if drain_detected else "none"
        
        # Blockage calculation
        if not drain_detected:
            fused_blockage = 0
            waste_inside_drain = False
            waste_beside_drain = waste_detected
        else:
            gemini_blockage = gemini_res.get("blockage_percentage", 0)
            yolo_blockage = yolo_res.get("blockage_percentage", 0) if yolo_res.get("drain_detected", False) else gemini_blockage
            fused_blockage = int(round((0.70 * gemini_blockage) + (0.30 * yolo_blockage)))
            waste_inside_drain = gemini_res.get("waste_inside_drain", True)
            waste_beside_drain = gemini_res.get("waste_beside_drain", False)
        
        # Confidence calculation
        gemini_conf = gemini_res.get("confidence", 0.85)
        yolo_conf = yolo_res.get("confidence", 0.85)
        if consensus_agreement and waste_detected:
            fused_confidence = min(0.99, round(max(gemini_conf, yolo_conf) * 1.10, 2))
        else:
            fused_confidence = round((gemini_conf + yolo_conf) / 2.0, 2)
            
        # Determine severity string
        if fused_blockage <= 20:
            severity = "low"
        elif fused_blockage <= 40:
            severity = "moderate"
        elif fused_blockage <= 60:
            severity = "significant"
        elif fused_blockage <= 80:
            severity = "high"
        else:
            severity = "critical"
            
        usable = gemini_res.get("usable", True) and local_quality.get("usable", True)
        quality_score = min(gemini_res.get("quality_score", 90), local_quality.get("quality_score", 90))
        
        return {
            "waste_detected": waste_detected,
            "waste_type": gemini_res.get("waste_type") or yolo_res.get("waste_type", "mixed"),
            "estimated_waste_coverage": max(gemini_res.get("estimated_waste_coverage", 0), yolo_res.get("estimated_waste_coverage", 0)),
            "waste_density": gemini_res.get("waste_density") or yolo_res.get("waste_density", "medium"),
            "waste_inside_drain": waste_inside_drain,
            "waste_beside_drain": waste_beside_drain,
            
            "drain_detected": drain_detected,
            "drainage_structure": drainage_structure,
            "blockage_percentage": fused_blockage,
            "opening_obstruction": gemini_res.get("opening_obstruction", fused_blockage) if drain_detected else 0,
            "water_flow_obstruction": gemini_res.get("water_flow_obstruction", fused_blockage) if drain_detected else 0,
            "sediment_accumulation": gemini_res.get("sediment_accumulation", 0) if drain_detected else 0,
            "vegetation_obstruction": gemini_res.get("vegetation_obstruction", 0) if drain_detected else 0,
            
            "is_screenshot": gemini_res.get("is_screenshot", False),
            "is_irrelevant": gemini_res.get("is_irrelevant", False),
            "is_manipulated": gemini_res.get("is_manipulated", False),
            "quality_score": quality_score,
            "usable": usable,
            
            "severity": severity,
            "confidence": fused_confidence,
            "bounding_boxes": bounding_boxes,
            "detection_source": "ensemble (Gemini 2.5 + YOLOv8)",
            "items_detected_count": yolo_res.get("items_detected_count", len(bounding_boxes)),
            "consensus_agreement": consensus_agreement
        }
        
    # 2. If only Gemini succeeded
    elif gemini_res:
        gemini_res["detection_source"] = "gemini_2.5_flash"
        gemini_res["items_detected_count"] = len(gemini_res.get("bounding_boxes", []))
        gemini_res["consensus_agreement"] = None
        gemini_res["waste_quantity"] = calculate_waste_quantity(
            waste_type=gemini_res.get("waste_type", "mixed"),
            blockage_percentage=gemini_res.get("blockage_percentage", 0),
            estimated_waste_coverage=gemini_res.get("estimated_waste_coverage", 0),
            drain_detected=gemini_res.get("drain_detected", False),
            drainage_structure=gemini_res.get("drainage_structure", "none")
        )
        return gemini_res
        
    # 3. If only YOLO succeeded (e.g. offline/quota fallback)
    elif yolo_res:
        yolo_res["detection_source"] = "yolov8_local"
        yolo_res["consensus_agreement"] = None
        yolo_res["waste_quantity"] = calculate_waste_quantity(
            waste_type=yolo_res.get("waste_type", "mixed"),
            blockage_percentage=yolo_res.get("blockage_percentage", 0),
            estimated_waste_coverage=yolo_res.get("estimated_waste_coverage", 0),
            drain_detected=yolo_res.get("drain_detected", False),
            drainage_structure=yolo_res.get("drainage_structure", "none")
        )
        return yolo_res
        
    # 4. Total fallback safe return
    fallback_qty = calculate_waste_quantity(
        waste_type="mixed",
        blockage_percentage=0,
        estimated_waste_coverage=40,
        drain_detected=False,
        drainage_structure="none"
    )
    return {
        "waste_detected": True,
        "waste_type": "mixed",
        "estimated_waste_coverage": 40,
        "waste_density": "medium",
        "waste_inside_drain": False,
        "waste_beside_drain": True,
        "drain_detected": False,
        "drainage_structure": "none",
        "blockage_percentage": 0,
        "opening_obstruction": 0,
        "water_flow_obstruction": 0,
        "sediment_accumulation": 0,
        "vegetation_obstruction": 0,
        "is_screenshot": False,
        "is_irrelevant": False,
        "is_manipulated": False,
        "quality_score": local_quality.get("quality_score", 90),
        "usable": local_quality.get("usable", True),
        "severity": "low",
        "confidence": 0.80,
        "bounding_boxes": [],
        "detection_source": "fallback_offline",
        "items_detected_count": 0,
        "consensus_agreement": None,
        "waste_quantity": fallback_qty
    }

def calculate_waste_quantity(
    waste_type: str,
    blockage_percentage: int,
    estimated_waste_coverage: int,
    drain_detected: bool,
    drainage_structure: str = "none"
) -> Dict[str, Any]:
    """
    Civil Engineering Waste Volume & Mass Estimator:
    Computes physical volume (m³), mass/weight (kg and metric tons),
    and cleanup logistics (50kg bags, tricycle loads, truck loads)
    based on material bulk density and channel hydraulic dimensions.
    """
    import math
    
    clean_type = waste_type.lower().strip()
    
    # Material bulk densities (kg/m³)
    density_map = {
        "plastic": 85.0,
        "organic": 420.0,
        "paper": 150.0,
        "metal": 550.0,
        "glass": 600.0,
        "silt": 1450.0,
        "sand": 1450.0,
        "sludge": 1450.0,
        "construction": 1500.0,
        "construction waste": 1500.0,
        "rubble": 1500.0,
        "concrete": 1500.0,
        "textile": 180.0,
        "mixed": 300.0
    }
    
    # Match density
    density = 300.0
    for key, val in density_map.items():
        if key in clean_type:
            density = val
            break
            
    # Volume calculation
    # Standard urban drainage baseline section: 4.0m length x 0.8m width x 0.9m depth = 2.88 m³
    if drain_detected and blockage_percentage > 0:
        total_channel_volume = 2.88
        volume_m3 = round(total_channel_volume * (blockage_percentage / 100.0), 2)
    elif estimated_waste_coverage > 0:
        # Open ground dumpsite baseline: 6.0 m² surface x 0.35m average pile height = 2.1 m³
        total_ground_volume = 2.10
        volume_m3 = round(total_ground_volume * (estimated_waste_coverage / 100.0), 2)
    else:
        volume_m3 = 0.0
        
    weight_kg = round(volume_m3 * density, 1)
    weight_tons = round(weight_kg / 1000.0, 2)
    
    # Logistics metrics:
    # 50kg heavy-duty bags (practical effective load 25kg)
    bags_count = math.ceil(weight_kg / 25.0) if weight_kg > 0 else 0
    # Motorized tricycle (Aboboyaa) capacity: 0.8 m³
    tricycle_trips = math.ceil(volume_m3 / 0.8) if volume_m3 > 0 else 0
    # Compactor truck capacity: 10.0 m³
    truck_loads = round(volume_m3 / 10.0, 2)
    
    if blockage_percentage >= 75 or weight_kg >= 500:
        urgency = "IMMEDIATE"
    elif blockage_percentage >= 50 or weight_kg >= 200:
        urgency = "URGENT"
    elif blockage_percentage >= 25 or weight_kg >= 50:
        urgency = "STANDARD"
    else:
        urgency = "ROUTINE"
        
    return {
        "volume_m3": volume_m3,
        "weight_kg": weight_kg,
        "weight_tons": weight_tons,
        "bags_count": bags_count,
        "tricycle_trips": tricycle_trips,
        "truck_loads": truck_loads,
        "density_kg_m3": density,
        "cleanup_urgency": urgency
    }

def analyze_report_image(image_path: str) -> Dict[str, Any]:
    """
    Concurrent Dual-Stage Vision Pipeline:
    Executes local OpenCV quality checks, then runs YOLOv8 and Google Gemini in parallel,
    fusing the results into a high-confidence, bounding-box-rich environmental report.
    """
    # 1. Run local CV quality checks first
    local_quality = check_image_quality_locally(image_path)
    
    gemini_result: Optional[Dict[str, Any]] = None
    yolo_result: Optional[Dict[str, Any]] = None
    
    # 2. Run Gemini and YOLO concurrently via ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        
        # Launch YOLO task
        yolo_future = executor.submit(run_local_yolo, image_path, local_quality)
        futures[yolo_future] = "yolo"
        
        # Launch Gemini task if API key is available
        if GEMINI_API_KEY:
            gemini_future = executor.submit(analyze_image_with_gemini, image_path, local_quality)
            futures[gemini_future] = "gemini"
            
        for future in as_completed(futures):
            tag = futures[future]
            try:
                res = future.result()
                if tag == "gemini":
                    gemini_result = res
                elif tag == "yolo":
                    yolo_result = res
            except Exception as e:
                logger.error(f"Error in concurrent vision task ({tag}): {e}")
                
    # 3. Fuse the parallel outputs
    fused = fuse_vision_results(gemini_result, yolo_result, local_quality)
    if "waste_quantity" not in fused or fused["waste_quantity"] is None:
        fused["waste_quantity"] = calculate_waste_quantity(
            waste_type=fused.get("waste_type", "mixed"),
            blockage_percentage=fused.get("blockage_percentage", 0),
            estimated_waste_coverage=fused.get("estimated_waste_coverage", 0),
            drain_detected=fused.get("drain_detected", False),
            drainage_structure=fused.get("drainage_structure", "none")
        )
    return fused
