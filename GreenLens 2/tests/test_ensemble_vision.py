import os
import sys
import numpy as np
import cv2
from PIL import Image

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vision_service import (
    check_image_quality_locally,
    fuse_vision_results,
    analyze_report_image
)
from services.verification_service import verify_cleanup
from schemas.report_schema import AiAnalysisResult, VerifyCleanupResponse

def create_dummy_image(filepath: str, color=(120, 150, 100)):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img = np.full((300, 300, 3), color, dtype=np.uint8)
    # Draw some shapes to simulate objects
    cv2.rectangle(img, (50, 50), (150, 150), (20, 40, 200), -1)
    cv2.imwrite(filepath, img)

def test_opencv_quality():
    test_img = os.path.join("scratch", "test_quality.jpg")
    create_dummy_image(test_img)
    quality = check_image_quality_locally(test_img)
    print("Quality check result:", quality)
    assert quality["quality_score"] > 0
    assert "usable" in quality
    print("[PASSED] OpenCV Quality Check passed!")

def test_ensemble_fusion_both_succeed():
    local_q = {"quality_score": 95, "usable": True}
    
    gemini_mock = {
        "waste_detected": True,
        "waste_type": "plastic",
        "estimated_waste_coverage": 50,
        "waste_density": "high",
        "waste_inside_drain": True,
        "waste_beside_drain": False,
        "drain_detected": True,
        "drainage_structure": "concrete channel",
        "blockage_percentage": 70,
        "opening_obstruction": 70,
        "water_flow_obstruction": 75,
        "sediment_accumulation": 30,
        "vegetation_obstruction": 15,
        "is_screenshot": False,
        "is_irrelevant": False,
        "is_manipulated": False,
        "quality_score": 92,
        "usable": True,
        "severity": "high",
        "confidence": 0.88,
        "bounding_boxes": [[100, 100, 400, 400, "plastic_bottle"]]
    }
    
    yolo_mock = {
        "waste_detected": True,
        "waste_type": "plastic",
        "estimated_waste_coverage": 40,
        "waste_density": "medium",
        "waste_inside_drain": True,
        "waste_beside_drain": False,
        "drain_detected": True,
        "drainage_structure": "open gutter",
        "blockage_percentage": 50,
        "opening_obstruction": 50,
        "water_flow_obstruction": 55,
        "sediment_accumulation": 20,
        "vegetation_obstruction": 10,
        "is_screenshot": False,
        "is_irrelevant": False,
        "is_manipulated": False,
        "quality_score": 90,
        "usable": True,
        "severity": "moderate",
        "confidence": 0.90,
        "bounding_boxes": [
            [100, 100, 200, 200, "bottle"],
            [250, 250, 350, 350, "can"]
        ],
        "items_detected_count": 2
    }
    
    fused = fuse_vision_results(gemini_mock, yolo_mock, local_q)
    print("Fused Result:", fused)
    
    assert fused["waste_detected"] is True
    assert fused["detection_source"] == "ensemble (Gemini 2.5 + YOLOv8)"
    assert fused["consensus_agreement"] is True
    # Confidence should be boosted (0.90 * 1.10 = 0.99)
    # Fused blockage: 0.70 * 70 + 0.30 * 50 = 49 + 15 = 64
    assert fused["blockage_percentage"] == 64
    assert fused["items_detected_count"] == 2
    assert len(fused["bounding_boxes"]) == 2
    print("[PASSED] Ensemble Fusion test passed!")

def test_ensemble_cleanup_verification():
    before_img = os.path.join("scratch", "before_drain.jpg")
    after_img = os.path.join("scratch", "after_drain.jpg")
    create_dummy_image(before_img, color=(80, 80, 80))
    create_dummy_image(after_img, color=(200, 220, 200))
    
    v_res = verify_cleanup(before_img, after_img)
    print("Cleanup verification result:", v_res)
    
    assert "cleanup_verified" in v_res
    assert "estimated_improvement" in v_res
    assert "explanation" in v_res
    assert "verification_source" in v_res
    print("[PASSED] Ensemble Cleanup Verification test passed!")

if __name__ == "__main__":
    test_opencv_quality()
    test_ensemble_fusion_both_succeed()
    test_ensemble_cleanup_verification()
    print("\nALL ENSEMBLE VISION TESTS PASSED SUCCESSFULLY!")
