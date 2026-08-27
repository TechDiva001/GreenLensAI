import logging
from typing import Dict, Any
from config import (
    WEIGHT_BLOCKAGE,
    WEIGHT_RAINFALL,
    WEIGHT_HISTORICAL,
    WEIGHT_CAPACITY,
    WEIGHT_ACCUMULATION,
    WEIGHT_LOCATION
)

logger = logging.getLogger(__name__)

def calculate_flood_risk_v2(
    blockage_percentage: float,
    rain_forecast_mm: float,
    historical_flooding: bool,
    capacity_restored: float,      # from the nearest drain segment
    accumulation_count: int,       # recurring reports at this location
    proximity_level: str           # geospatial proximity: CRITICAL, HIGH, MODERATE, LOW
) -> Dict[str, Any]:
    """
    Advanced flood risk calculation mapping exactly to the 6 weighted PRD variables.
    """
    # 1. Blockage contribution (35%)
    blockage_contrib = blockage_percentage * WEIGHT_BLOCKAGE
    
    # 2. Rainfall forecast contribution (30%)
    # Map rain mm to 0-100 scale (e.g. 25mm of rain is max contribution)
    scaled_rainfall = min(100.0, rain_forecast_mm * 4.0)
    rainfall_contrib = scaled_rainfall * WEIGHT_RAINFALL
    
    # 3. Historical flood contribution (15%)
    historical_val = 100.0 if historical_flooding else 0.0
    historical_contrib = historical_val * WEIGHT_HISTORICAL
    
    # 4. Drain capacity contribution (10%)
    # Less capacity restored = more risk. Map 0-100 capacity.
    capacity_val = 100.0 - capacity_restored
    capacity_contrib = capacity_val * WEIGHT_CAPACITY
    
    # 5. Waste accumulation contribution (5%)
    # Accumulation count (number of recurring reports in cluster) maps to 0-100
    accum_val = min(100.0, accumulation_count * 20.0)
    accumulation_contrib = accum_val * WEIGHT_ACCUMULATION
    
    # 6. Location characteristics / proximity contribution (5%)
    proximity_map = {
        "CRITICAL": 100.0,
        "HIGH": 75.0,
        "MODERATE": 40.0,
        "LOW": 10.0
    }
    proximity_val = proximity_map.get(proximity_level.upper(), 10.0)
    location_contrib = proximity_val * WEIGHT_LOCATION
    
    # Sum up total score
    total_score = round(
        blockage_contrib +
        rainfall_contrib +
        historical_contrib +
        capacity_contrib +
        accumulation_contrib +
        location_contrib,
        1
    )
    total_score = min(100.0, total_score)
    
    # Set risk level categories
    if total_score <= 20.0:
        risk_level = "LOW"
    elif total_score <= 40.0:
        risk_level = "MODERATE"
    elif total_score <= 60.0:
        risk_level = "SIGNIFICANT"
    elif total_score <= 80.0:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"
        
    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "contributions": {
            "blockage_pct": round(blockage_contrib, 1),
            "rainfall_pct": round(rainfall_contrib, 1),
            "historical_pct": round(historical_contrib, 1),
            "capacity_pct": round(capacity_contrib, 1),
            "accumulation_pct": round(accumulation_contrib, 1),
            "location_pct": round(location_contrib, 1)
        }
    }

def predict_maintenance_window(
    blockage_percentage: float,
    accumulation_count: int,
    historical_flooding: bool
) -> Dict[str, Any]:
    """
    Predicts when a drain segment will require cleaning (AI Function #18).
    Uses a simple regression model to estimate days until critical blockage (80%).
    """
    if blockage_percentage >= 80.0:
        return {
            "days_until_critical": 0,
            "maintenance_required": True,
            "prediction_message": "Immediate cleanup required: Drain is critically blocked."
        }
        
    # Growth rate of blockage per day (heuristic based on report volume and history)
    # Base accumulation of 1% per day
    # Accumulation reports accelerate rate by 0.5% per day
    # Historical areas accumulate faster by 0.3% per day
    daily_accumulation_rate = 1.0 + (accumulation_count * 0.5) + (0.3 if historical_flooding else 0.0)
    
    remaining_blockage_capacity = 80.0 - blockage_percentage
    days_until_critical = max(1, int(remaining_blockage_capacity / daily_accumulation_rate))
    
    return {
        "days_until_critical": days_until_critical,
        "maintenance_required": days_until_critical <= 14,
        "prediction_message": f"Drain is likely to require cleaning within the next {days_until_critical} days."
    }
