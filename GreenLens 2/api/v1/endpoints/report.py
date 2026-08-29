from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from schemas.report_schema import AnalyzeImageRequest, AiAnalysisResult
from services.report_service import process_analyze_image, process_analyze_image_generator
import logging
import json

logger = logging.getLogger("GreenLensAI_V2")
router = APIRouter()

@router.post("/analyze-image", response_model=AiAnalysisResult)
async def analyze_image(req: AnalyzeImageRequest):
    """
    Analyzes a report image URL synchronously.
    """
    try:
        result = process_analyze_image(req)
        return result
    except ValueError as ve:
        logger.warning(f"Validation error in analyze-image API: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception("Unexpected error in analyze-image API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.post("/analyze-image-stream")
async def analyze_image_stream(req: AnalyzeImageRequest):
    """
    Streams stage-by-stage analysis progress events using Server-Sent Events (SSE).
    """
    async def event_publisher():
        async for event in process_analyze_image_generator(req):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
