from fastapi import APIRouter, HTTPException, status
from schemas.report_schema import AnalyzeImageRequest, AiAnalysisResult
from services.report_service import process_analyze_image
import logging

logger = logging.getLogger("GreenLensAI_V2")
router = APIRouter()

@router.post("/analyze-image", response_model=AiAnalysisResult)
async def analyze_image(req: AnalyzeImageRequest):
    """
    Analyzes a report image URL and writes to Supabase.
    """
    try:
        result = process_analyze_image(req)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception("Error in analyze-image API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
