from fastapi import APIRouter
from .endpoints import report, verification, assistant, weather

api_router = APIRouter()

# Mount all endpoints under their PRD-defined route prefixes
api_router.include_router(report.router, prefix="/ai", tags=["ai"])
api_router.include_router(verification.router, prefix="/ai", tags=["verification"])
api_router.include_router(assistant.router, prefix="/ai/assistant", tags=["assistant"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
