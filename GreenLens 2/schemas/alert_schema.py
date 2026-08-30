from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AlertKeyMetrics(BaseModel):
    rain_24h_mm: float = 0.0
    surcharge_ratio: float = 0.0
    overtopping_probability: int = 0
    hydrograph_peak_mm_h: float = 0.0

class FloodAlertPayload(BaseModel):
    alert_severity: str = Field("NONE", description="NONE, INFO, MODERATE, HIGH, CRITICAL")
    should_alert: bool = Field(False, description="True if conditions exceed notification threshold")
    title: str = Field("", description="Push notification title")
    message: str = Field("", description="Actionable alert message body")
    key_metrics: AlertKeyMetrics = Field(default_factory=AlertKeyMetrics)
    time_to_overflow_hours: float = Field(24.0, description="Hours remaining before culvert overtopping")
    safe_actions: List[str] = Field(default_factory=list, description="Recommended citizen safety actions")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of evaluation")
