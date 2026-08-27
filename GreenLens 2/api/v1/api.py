from fastapi import APIRouter
from .endpoints import report

api_router = APIRouter()
api_router.include_router(report.router, prefix="/ai", tags=["ai"])
