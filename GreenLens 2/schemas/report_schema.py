from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class AnalyzeImageRequest(BaseModel):
    image_url: str
    user_id: str
    municipality_id: str
    latitude: float
    longitude: float
    description: str = ""
    historical_flooding: bool = False

class VerifyCleanupRequest(BaseModel):
    report_id: str
    after_image_url: str
    before_image_url: Optional[str] = None

class VerifyCleanupResponse(BaseModel):
    report_id: str
    status: str
    verification_result: Dict[str, Any]
    verified: bool
    improvement_percentage: int
    explanation: str
    consensus_verified: Optional[bool] = None
    verification_source: Optional[str] = "ensemble (Gemini 2.5 + YOLOv8)"

class AiAnalysisResult(BaseModel):
    report_id: str
    status: str = "SUBMITTED"
    fraud_flag: bool = False
    waste_detected: bool = False
    waste_type: str = "none"
    blockage_percentage: int = 0
    risk_score: float = 0.0
    risk_level: str = "LOW"
    nearest_segment_name: Optional[str] = None
    proximity_level: Optional[str] = None
    proximity_distance_meters: Optional[float] = None
    confidence: float = 0.90
    quality_score: int = 90
    usable: bool = True
    maintenance_message: Optional[str] = None
    days_until_critical: Optional[int] = None
    rain_24h_mm: float = 0.0
    rain_probability_24h: int = 0
    bounding_boxes: List[Any] = []
    dispatch_recommendation: Optional[Dict[str, Any]] = None
    risk_contributions: Optional[Dict[str, Any]] = None
    detection_source: Optional[str] = "ensemble (Gemini 2.5 + YOLOv8)"
    items_detected_count: Optional[int] = 0
    consensus_agreement: Optional[bool] = None

# Weather Schemas
class WeatherDailyForecast(BaseModel):
    date: Optional[str] = None
    max_temp_c: Optional[float] = None
    min_temp_c: Optional[float] = None
    avg_temp_c: Optional[float] = None
    total_precip_mm: Optional[float] = 0.0
    chance_of_rain: Optional[int] = 0
    condition_text: Optional[str] = "Clear"
    condition_icon: Optional[str] = ""

class WeatherCurrentResponse(BaseModel):
    source: str = "WeatherAPI"
    location: Dict[str, Any]
    current: Dict[str, Any]

class WeatherForecastResponse(BaseModel):
    source: str = "WeatherAPI"
    location: Dict[str, Any]
    current: Dict[str, Any]
    rain_24h_mm: float
    rain_48h_mm: float
    rain_probability_24h: int
    rain_probability_48h: int
    daily_forecast: List[WeatherDailyForecast] = []

# Assistant Schemas
class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = []

class DailySummaryResponse(BaseModel):
    summary: str
    timestamp: str
    report_count: int
    critical_count: int
    high_count: int
