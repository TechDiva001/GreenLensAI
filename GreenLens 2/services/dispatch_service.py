import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def generate_dispatch_recommendation(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates automated dispatch recommendations and urgency window based on incident details (AI Function #14).
    """
    risk_score = incident.get("risk_score", 0.0)
    risk_level = incident.get("risk_level", "LOW")
    blockage = incident.get("blockage_percentage", 0)
    rain_forecast = incident.get("rain_24h_mm", 0.0)
    historical = incident.get("historical_flooding", False)
    nearest_segment = incident.get("nearest_segment_id", "D-102")
    
    # Urgency matching documentation rules
    if risk_level == "CRITICAL":
        team = "Emergency Action Team 1"
        timeframe_hours = 6
    elif risk_level == "HIGH":
        team = "Rapid Response Team 2"
        timeframe_hours = 12
    elif risk_level == "SIGNIFICANT":
        team = "Municipal Clean Team 3"
        timeframe_hours = 24
    elif risk_level == "MODERATE":
        team = "Standard Maintenance Team 4"
        timeframe_hours = 48
    else:
        team = "Routine Inspection Team 5"
        timeframe_hours = 72

    reasons = []
    if blockage >= 60:
        reasons.append(f"{blockage}% drainage blockage restricts water-flow")
    else:
        reasons.append(f"Minor blockage of {blockage}% detected")
        
    if rain_forecast >= 15.0:
        reasons.append(f"Heavy rainfall ({rain_forecast} mm) predicted in forecast window")
    elif rain_forecast >= 5.0:
        reasons.append(f"Moderate rainfall ({rain_forecast} mm) expected")
        
    if historical:
        reasons.append("Segment located in a high-risk historical flooding area")
        
    action_text = f"Dispatch {team} to Drainage Segment {nearest_segment} within {timeframe_hours} hours."
    
    # Generate Alerts (AI Function #24)
    alerts = []
    if risk_level in ["HIGH", "CRITICAL"]:
        alerts.append({
            "target": "Municipal Officers",
            "alert_level": "CRITICAL ALERT",
            "title": f"High Flood Risk Alert at {nearest_segment}",
            "message": f"Critical blockages and high rainfall forecasts require dispatch within {timeframe_hours} hours."
        })
        alerts.append({
            "target": "Citizens",
            "alert_level": "WARNING",
            "title": "Local Flood Warning",
            "message": f"Heavy rainfall is expected near {nearest_segment}. Avoid low-lying areas near the affected drainage channel."
        })
        
    return {
        "recommended_action": action_text,
        "team_assigned": team,
        "urgency_window_hours": timeframe_hours,
        "reasons": reasons,
        "alerts": alerts
    }

def prioritize_incidents(incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sorts a list of incidents by risk score descending and generates dispatches (AI Function #13).
    """
    sorted_incidents = sorted(incidents, key=lambda x: x.get("risk_score", 0.0), reverse=True)
    
    for incident in sorted_incidents:
        incident["dispatch_recommendation"] = generate_dispatch_recommendation(incident)
        
    return sorted_incidents
