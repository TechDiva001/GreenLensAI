import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.api import api_router
from core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GreenLensAI_V2")

app = FastAPI(
    title="GreenLens AI Advanced Backend (V2)",
    description="Comprehensive AI Backend Services (all 25 AI functions and 7 workstreams)",
    version="2.0.1"
)

# Enable CORS for phone Wi-Fi connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.1",
        "vision_engine": "Gemini 2.5/1.5 Flash (Cloud)" if settings.GEMINI_API_KEY else "Local YOLOv8 + OpenCV (Offline Fallback)",
        "weather_engine": "Open-Meteo (Free, No Key)",
        "optimization_engine": "Local greedy TSP",
        "assistant_engine": "Gemini RAG" if settings.GEMINI_API_KEY else "Keyword Heuristic Fallback"
    }

# Include routers
app.include_router(api_router, prefix="/api")

# Legacy endpoints mapping or remaining endpoints could be added here
