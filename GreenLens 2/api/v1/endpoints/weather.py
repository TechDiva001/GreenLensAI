import logging
from fastapi import APIRouter, Query, HTTPException, status
from schemas.report_schema import WeatherForecastResponse, WeatherCurrentResponse
from services.weather_service import get_weather_forecast

logger = logging.getLogger("GreenLensAI_V2")
router = APIRouter()

@router.get("/forecast", response_model=WeatherForecastResponse)
async def get_forecast(
    latitude: float = Query(default=5.6037, description="Latitude of the location"),
    longitude: float = Query(default=-0.1870, description="Longitude of the location")
):
    """
    Fetches real-time weather, 24h & 48h rainfall estimates, and daily forecast using WeatherAPI.
    """
    try:
        data = get_weather_forecast(latitude, longitude)
        return WeatherForecastResponse(**data)
    except Exception as e:
        logger.exception("Error in weather forecast endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch weather forecast: {str(e)}"
        )

@router.get("/current", response_model=WeatherCurrentResponse)
async def get_current_weather(
    latitude: float = Query(default=5.6037, description="Latitude of the location"),
    longitude: float = Query(default=-0.1870, description="Longitude of the location")
):
    """
    Fetches current weather observations for a specific coordinate.
    """
    try:
        data = get_weather_forecast(latitude, longitude)
        return WeatherCurrentResponse(
            source=data.get("source", "WeatherAPI"),
            location=data.get("location", {}),
            current=data.get("current", {})
        )
    except Exception as e:
        logger.exception("Error in weather current endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch current weather: {str(e)}"
        )
