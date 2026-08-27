from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class AnalyzeImageRequest(BaseModel):
    image_url: str
    user_id: str
    latitude: float
    longitude: float
    description: str = ""
    historical_flooding: bool = False

class VerifyCleanupRequest(BaseModel):
    report_id: str
    after_image_url: str

class AiAnalysisResult(BaseModel):
    report_id: str
    status: str
    fraud_flag: bool
    waste_detected: bool
    waste_type: str
    blockage_percentage: int
    risk_score: float
    risk_level: str
    nearest_segment_name: Optional[str] = None
    proximity_level: Optional[str] = None
    proximity_distance_meters: Optional[float] = None
    confidence: float
    quality_score: int
    usable: bool
    maintenance_message: Optional[str] = None
    days_until_critical: Optional[int] = None
    rain_24h_mm: float
    rain_probability_24h: int
    bounding_boxes: List[Any] = []
    dispatch_recommendation: Optional[Dict[str, Any]] = None
    risk_contributions: Optional[Dict[str, Any]] = None
