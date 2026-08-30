from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class FloodEventHistoryCreate(BaseModel):
    municipality_id: Optional[int] = None
    drainage_segment_id: Optional[int] = None
    catchment_name: str = "Winneba Catchment"
    latitude: float = 5.34352
    longitude: float = -0.62566
    event_timestamp: Optional[datetime] = None
    severity: str = Field(..., description="NONE, INFO, MODERATE, HIGH, CRITICAL")
    compound_risk_score: float = Field(..., ge=0, le=100)
    surcharge_ratio: float = 0.0
    overtopping_probability_percent: int = Field(0, ge=0, le=100)
    time_to_overflow_hours: float = 24.0
    effective_capacity_m3s: Optional[float] = 0.0
    nominal_capacity_m3s: Optional[float] = 12.5
    storm_inflow_q_m3s: Optional[float] = 0.0
    rainfall_24h_mm: Optional[float] = 0.0
    rainfall_intensity_mm_h: Optional[float] = 0.0
    rainfall_probability_24h: Optional[int] = 0
    crowdsourced_blockage_percent: Optional[float] = 0.0
    nearby_reports_count: Optional[int] = 0
    verified_cleanups_count: Optional[int] = 0
    primary_waste_type: Optional[str] = None
    event_status: str = Field("PREDICTED", description="PREDICTED, CONFIRMED_FLOOD, MITIGATED, CLEARED, FALSE_POSITIVE")
    mitigation_actions: List[str] = []
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}

class FloodEventHistoryResponse(FloodEventHistoryCreate):
    id: int
    created_at: datetime
