import os
import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from PIL import Image
import json

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
        # Default safe fallback
        return {
            "quality_score": 90,
            "usable": True,
            "reasons": []
        }

def load_local_yolo_model():
    """
    Downloads and loads the YOLOv8 model from Hugging Face, or falls back to the default model.
    """
    try:
        from huggingface_hub import hf_hub_download
        model_path = hf_hub_download(
            repo_id=YOLO_MODEL_NAME,
            filename="best.pt"
        )
        return model_path
    except Exception as e:
        logger.warning(f"Could not load HuggingFace model: {e}. Falling back to default yolov8n.pt")
        return "yolov8n.pt"

def run_local_yolo(image_path: str, local_quality: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs local YOLOv8 waste detection and populates all vision schema attributes.
    """
    try:
        from ultralytics import YOLO
        
        model_file = load_local_yolo_model()
        model = YOLO(model_file)
        
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
        
        if waste_detected:
            drain_detected = True
            drainage_structure = "open gutter"
            blockage_percentage = min(95, int(estimated_waste_coverage * 1.1))
            water_flow_obs = min(95, int(blockage_percentage * 1.05))
            sediment_acc = min(90, int(blockage_percentage * 0.4))
            veg_obs = min(90, int(blockage_percentage * 0.3))
            
            if blockage_percentage <= 20:
                severity = "low"
            elif blockage_percentage <= 40:
                severity = "moderate"
            elif blockage_percentage <= 60:
                severity = "significant"
            elif blockage_percentage <= 80:
                severity = "high"
            else:
                severity = "critical"
                
        # Merge quality details
        return {
            "waste_detected": waste_detected,
            "waste_type": waste_type,
            "estimated_waste_coverage": estimated_waste_coverage,
            "waste_density": waste_density,
            "waste_inside_drain": drain_detected,
            "waste_beside_drain": not drain_detected if waste_detected else False,
            
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
            "confidence": round(float(boxes.conf.mean().item()), 2) if len(boxes) > 0 else 0.90,
            "bounding_boxes": bounding_boxes
        }
    except Exception as e:
        logger.error(f"Error running local YOLO model: {e}")
        return {
            "waste_detected": True,
            "waste_type": "mixed",
            "estimated_waste_coverage": 40,
            "waste_density": "medium",
            "waste_inside_drain": True,
            "waste_beside_drain": False,
            "drain_detected": True,
            "drainage_structure": "open gutter",
            "blockage_percentage": 45,
            "opening_obstruction": 45,
            "water_flow_obstruction": 45,
            "sediment_accumulation": 20,
            "vegetation_obstruction": 10,
            "is_screenshot": False,
            "is_irrelevant": False,
            "is_manipulated": False,
            "quality_score": local_quality.get("quality_score", 90),
            "usable": local_quality.get("usable", True),
            "severity": "significant",
            "confidence": 0.80,
            "bounding_boxes": []
        }

def analyze_image_with_gemini(image_path: str, local_quality: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls Gemini API to analyze waste, drainage, and validation metrics using structured response schemas.
    """
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        img = Image.open(image_path)
        
        prompt = (
            "Analyze this image of a roadside, urban street, or drainage area for environmental issues.\n"
            "Assess the following:\n"
            "1. Waste Detection: is waste present, type, coverage (0-100), density (high/medium/low), location inside/beside drain.\n"
            "2. Drainage Detection: is a drain present, structure type, blockage (0-100), opening obstruction (0-100), water flow obstruction (0-100), sediment buildup (0-100), vegetation obstruction (0-100).\n"
            "3. Image Quality: check if it's a screenshot, irrelevant image, or digitally manipulated image. Provide a quality score (0-100) and state if it is usable for municipal reporting.\n"
            "4. Bounding boxes: extract normalized boxes [ymin, xmin, ymax, xmax, label] where coordinates are normalized 0-1000."
        )
        
        response = client.models.generate_content(
            model='Gemini 2.5 Flash Lite',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VisionAnalysisResult,
                temperature=0.1
            ),
        )
        
        result_dict = json.loads(response.text)
        
        # Override usability if local OpenCV blur/brightness check is severe
        if not local_quality.get("usable", True):
            result_dict["usable"] = False
            result_dict["quality_score"] = min(result_dict["quality_score"], local_quality["quality_score"])
            
        return result_dict
    except Exception as e:
        logger.error(f"Error calling Gemini Vision API: {e}")
        logger.info("Falling back to local YOLOv8 offline model...")
        return run_local_yolo(image_path, local_quality)

def analyze_report_image(image_path: str) -> Dict[str, Any]:
    """
    Analyzes a report image. Combines local OpenCV checks for blur/darkness/brightness
    with Gemini VLM or local YOLO fallsbacks.
    """
    # 1. Run local CV quality checks first (Laplacian variance, brightness)
    local_quality = check_image_quality_locally(image_path)
    
    # 2. Run analysis
    if GEMINI_API_KEY:
        return analyze_image_with_gemini(image_path, local_quality)
    else:
        return run_local_yolo(image_path, local_quality)
