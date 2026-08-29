import os
import requests
import logging
from fastapi import APIRouter, HTTPException, status
from schemas.report_schema import VerifyCleanupRequest, VerifyCleanupResponse
from services.verification_service import verify_cleanup
from core.config import settings

logger = logging.getLogger("GreenLensAI_V2")
router = APIRouter()

def download_image_to_file(url: str, filepath: str) -> bool:
    try:
        # Check if local file
        if os.path.exists(url):
            import shutil
            shutil.copy(url, filepath)
            return True
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return False

@router.post("/verify-cleanup", response_model=VerifyCleanupResponse)
async def verify_report_cleanup(req: VerifyCleanupRequest):
    """
    Compares before and after images of a reported drain blockage to verify cleanup resolution.
    """
    try:
        report_id = req.report_id.strip()
        after_path = os.path.join(settings.UPLOAD_DIR, f"{report_id}_after.jpg")
        before_path = os.path.join(settings.UPLOAD_DIR, f"{report_id}_before.jpg")

        # 1. Download after image
        if not download_image_to_file(req.after_image_url, after_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to download or access after image: {req.after_image_url}"
            )

        # 2. Check for before image
        if not os.path.exists(before_path):
            if req.before_image_url:
                if not download_image_to_file(req.before_image_url, before_path):
                    logger.warning(f"Could not download before_image_url: {req.before_image_url}")
            if not os.path.exists(before_path):
                # Fallback: if before image is missing, we use after image as base reference
                before_path = after_path

        # 3. Run verification service
        v_res = verify_cleanup(before_path, after_path)
        
        improvement = int(v_res.get("estimated_improvement", 0))
        is_verified = bool(v_res.get("cleanup_verified", False))
        explanation = str(v_res.get("explanation", "Verification completed."))

        return VerifyCleanupResponse(
            report_id=report_id,
            status="VERIFIED" if is_verified else "REJECTED",
            verification_result=v_res,
            verified=is_verified,
            improvement_percentage=improvement,
            explanation=explanation,
            consensus_verified=v_res.get("consensus_verified"),
            verification_source=v_res.get("verification_source", "ensemble (Gemini 2.5 + YOLOv8)")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during cleanup verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )
