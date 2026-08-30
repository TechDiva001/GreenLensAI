from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class HydrographPoint(BaseModel):
    time: str = Field(..., description="ISO or HH:MM timestamp")
    hour: str = Field(..., description="Human-readable hour e.g. 14:00")
    precipitation_mm: float = Field(..., description="Hourly rainfall rate in mm/h")
    rain_probability: int = Field(..., description="Precipitation probability (0-100%)")
    is_surcharge_threat: bool = Field(..., description="True if precipitation >= 3.0 mm/h")
    runoff_intensity: str = Field(..., description="SAFE (<3mm), WARNING (3-5mm), DANGER (>=5mm)")

class OpenMeteoLocation(BaseModel):
    name: str = "Winneba Catchment"
    lat: float = 5.34352
    lon: float = -0.62566
    elevation: Optional[float] = 15.0
    timezone: Optional[str] = "UTC"

class OpenMeteoCurrent(BaseModel):
    temp_c: float = 28.0
    feelslike_c: Optional[float] = 30.0
    humidity: int = 78
    wind_kph: float = 12.0
    precipitation_mm: float = 0.0
    weather_code: int = 0
    condition_text: str = "Clear"
    condition_icon: str = "☀️"
    condition_slug: str = "clear"
    is_day: int = 1

class OpenMeteoTelemetryResponse(BaseModel):
    source: str = "Open-Meteo v1"
    is_fallback: bool = False
    location: OpenMeteoLocation
    current: OpenMeteoCurrent
    rain_24h_mm: float = 0.0
    rain_48h_mm: float = 0.0
    rain_probability_24h: int = 0
    rain_probability_48h: int = 0
    hydrograph: List[HydrographPoint] = []

class CompoundFloodRequest(BaseModel):
    nominal_capacity_m3s: float = Field(12.5, description="Nominal discharge capacity (m^3/s)")
    blockage_percent: float = Field(40.0, description="Blockage percentage (0 - 100%)")
    catchment_area_ha: float = Field(15.0, description="Catchment drainage surface area (hectares)")
    rain_intensity_mm_h: Optional[float] = Field(None, description="Rolling rainfall intensity (mm/h). Derived from live Open-Meteo if null.")
    latitude: float = Field(5.34352, description="Latitude (Default: Winneba, Ghana)")
    longitude: float = Field(-0.62566, description="Longitude (Default: Winneba, Ghana)")
    runoff_coefficient: float = Field(0.75, description="Rational method runoff coefficient C")

class CompoundHydrologyResult(BaseModel):
    nominal_capacity_m3s: float
    effective_capacity_m3s: float
    storm_inflow_q_m3s: float
    surcharge_ratio: float
    overtopping_probability_percent: int
    time_to_overflow_hours: float
    overflow_state: str
    compound_risk_score: float
    risk_level: str

class CompoundFloodResponse(BaseModel):
    telemetry: OpenMeteoTelemetryResponse
    hydrology: CompoundHydrologyResult
    advisories: List[str] = []

class DelugeSimulationRequest(BaseModel):
    storm_intensity_mm_h: float = Field(45.0, description="Simulated deluge storm intensity (10 to 120 mm/h)")
    desilting_cleanup_percent: float = Field(30.0, description="Simulated trash extraction improvement (0 to 80%)")
    nominal_capacity_m3s: float = Field(12.5, description="Nominal discharge capacity (m^3/s)")
    current_blockage_percent: float = Field(60.0, description="Baseline culvert blockage %")
    catchment_area_ha: float = Field(15.0, description="Catchment area in hectares")

class DelugeSimulationResponse(BaseModel):
    baseline_hydrology: CompoundHydrologyResult
    simulated_hydrology: CompoundHydrologyResult
    risk_reduction_percentage: float
    time_gain_hours: float
    mitigation_verdict: str
