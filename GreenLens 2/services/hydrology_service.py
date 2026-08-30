import logging
from typing import Dict, Any
from config import DEFAULT_RUNOFF_COEFFICIENT_C

logger = logging.getLogger(__name__)

def calculate_compound_flood_hydrology(
    nominal_capacity_m3s: float,
    blockage_percent: float,
    catchment_area_ha: float,
    rain_intensity_mm_h: float,
    runoff_coefficient: float = DEFAULT_RUNOFF_COEFFICIENT_C
) -> Dict[str, Any]:
    """
    Synthesizes meteorological rainfall with physical drainage constraints
    using the Rational Runoff Method (Q = CIA/360) and hydraulic culvert capacities.
    """
    # Clamp blockage percentage between 0% and 100%
    clamped_blockage = max(0.0, min(100.0, float(blockage_percent)))
    
    # 1. Effective Culvert Discharge Capacity (m^3/s)
    effective_cap = max(0.001, float(nominal_capacity_m3s) * (1.0 - (clamped_blockage / 100.0)))

    # 2. Catchment Storm Runoff Inflow Q (m^3/s)
    # Formula: Q = (C * I * A) / 360
    c_factor = float(runoff_coefficient)
    i_intensity = max(0.0, float(rain_intensity_mm_h))
    a_area = max(0.1, float(catchment_area_ha))
    storm_inflow_q = (c_factor * i_intensity * a_area) / 360.0

    # 3. Surcharge Ratio
    surcharge_ratio = round(storm_inflow_q / effective_cap, 3)

    # 4. Overtopping Probability (%)
    # Overtopping Probability (%) = min(99, round(Surcharge Ratio * 65 + Blockage * 0.35))
    raw_prob = (surcharge_ratio * 65.0) + (clamped_blockage * 0.35)
    overtopping_prob = int(min(99.0, max(0.0, round(raw_prob))))

    # 5. Time to Overflow Estimation
    if surcharge_ratio >= 1.2:
        time_to_overflow = round(max(0.5, 6.0 / surcharge_ratio), 1)
        overflow_state = "IMMINENT_OVERTOPPING"
    elif surcharge_ratio >= 0.8:
        # Interpolate between 8 and 12 hours
        time_to_overflow = round(8.0 + (1.2 - surcharge_ratio) * 10.0, 1)
        overflow_state = "BANK_SURCHARGE_WARNING"
    else:
        time_to_overflow = 24.0
        overflow_state = "STABLE_FLOW"

    # 6. Municipal Compound Risk Score (0 - 100)
    # Compound Risk Score = min(100, (Blockage * 0.45) + (Surcharge Ratio * 35) + Rainfall Factor)
    rainfall_factor = min(20.0, i_intensity * 2.0)
    compound_score = min(100.0, round((clamped_blockage * 0.45) + (surcharge_ratio * 35.0) + rainfall_factor, 1))

    if compound_score >= 75:
        risk_level = "CRITICAL"
    elif compound_score >= 55:
        risk_level = "HIGH"
    elif compound_score >= 35:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return {
        "nominal_capacity_m3s": round(float(nominal_capacity_m3s), 3),
        "effective_capacity_m3s": round(effective_cap, 3),
        "storm_inflow_q_m3s": round(storm_inflow_q, 3),
        "surcharge_ratio": surcharge_ratio,
        "overtopping_probability_percent": overtopping_prob,
        "time_to_overflow_hours": time_to_overflow,
        "overflow_state": overflow_state,
        "compound_risk_score": compound_score,
        "risk_level": risk_level
    }


def simulate_deluge_event(
    storm_intensity_mm_h: float,
    desilting_cleanup_percent: float,
    nominal_capacity_m3s: float,
    current_blockage_percent: float,
    catchment_area_ha: float
) -> Dict[str, Any]:
    """
    Simulates extreme downpour deluge events (10 to 120 mm/h) combined with
    proactive drain cleanup (0 to 80%) to measure time gained and risk reduction.
    """
    baseline = calculate_compound_flood_hydrology(
        nominal_capacity_m3s=nominal_capacity_m3s,
        blockage_percent=current_blockage_percent,
        catchment_area_ha=catchment_area_ha,
        rain_intensity_mm_h=storm_intensity_mm_h
    )

    mitigated_blockage = max(0.0, current_blockage_percent - desilting_cleanup_percent)
    simulated = calculate_compound_flood_hydrology(
        nominal_capacity_m3s=nominal_capacity_m3s,
        blockage_percent=mitigated_blockage,
        catchment_area_ha=catchment_area_ha,
        rain_intensity_mm_h=storm_intensity_mm_h
    )

    risk_reduction = round(max(0.0, baseline["compound_risk_score"] - simulated["compound_risk_score"]), 1)
    time_gain = round(max(0.0, simulated["time_to_overflow_hours"] - baseline["time_to_overflow_hours"]), 1)

    if simulated["risk_level"] in ["LOW", "MODERATE"] and baseline["risk_level"] in ["HIGH", "CRITICAL"]:
        verdict = f"Proactive desilting of {desilting_cleanup_percent}% successfully averts catastrophic overtopping during a {storm_intensity_mm_h} mm/h deluge event."
    elif risk_reduction > 15.0:
        verdict = f"Substantial mitigation: Extends time to overflow by +{time_gain} hrs and reduces risk score by {risk_reduction} pts."
    else:
        verdict = f"Partial mitigation: Rainfall intensity ({storm_intensity_mm_h} mm/h) exceeds standard culvert capacity. Upstream retention recommended."

    return {
        "baseline_hydrology": baseline,
        "simulated_hydrology": simulated,
        "risk_reduction_percentage": risk_reduction,
        "time_gain_hours": time_gain,
        "mitigation_verdict": verdict
    }


def evaluate_alert_severity(hydrology: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates multi-signal meteorological & hydrological telemetry against
    civil engineering thresholds to classify flood alert severity and generate
    actionable citizen warning payloads.
    """
    surcharge_ratio = float(hydrology.get("surcharge_ratio", 0.0))
    overtopping_prob = int(hydrology.get("overtopping_probability_percent", 0))
    time_to_overflow = float(hydrology.get("time_to_overflow_hours", 24.0))
    
    rain_24h = float(telemetry.get("rain_24h_mm", 0.0))
    rain_prob_24h = int(telemetry.get("rain_probability_24h", 0))
    
    hydrograph = telemetry.get("hydrograph", [])
    peak_hourly = 0.0
    if hydrograph:
        peak_hourly = max([float(h.get("precipitation_mm", 0.0)) for h in hydrograph[:12]])

    key_metrics = {
        "rain_24h_mm": round(rain_24h, 1),
        "surcharge_ratio": round(surcharge_ratio, 2),
        "overtopping_probability": overtopping_prob,
        "hydrograph_peak_mm_h": round(peak_hourly, 1)
    }

    # Evaluate severity ladder
    if surcharge_ratio >= 1.0 or overtopping_prob >= 90 or peak_hourly >= 5.0:
        severity = "CRITICAL"
        should_alert = True
        title = "🚨 CRITICAL FLOOD ALERT: Culvert Overtopping Threat"
        message = f"Conveyance capacity exceeded in your drainage basin. Overtopping probability is {overtopping_prob}% (Surcharge: {surcharge_ratio:.2f}x). Avoid low-lying crossings immediately."
        actions = [
            "Evacuate flood-prone culvert zones immediately (Winneba coastal roads & Odaw/Circle corridor).",
            "Move electrical appliances and livestock to elevated structures.",
            "Contact NADMO Disaster Response on emergency line 112 / 0302-772926.",
            "Do not drive or walk through moving floodwaters."
        ]
    elif overtopping_prob >= 65 or surcharge_ratio >= 0.8 or rain_24h >= 25.0:
        severity = "HIGH"
        should_alert = True
        title = "⚠️ HIGH FLOOD RISK ALERT: Drainage Surcharge Expected"
        message = f"Elevated stormwater approaching culvert capacity in your area (~{time_to_overflow:.1f}h to overtopping). Keep clear of open storm drains."
        actions = [
            "Avoid low-lying culvert crossings and unpaved drain banks.",
            "Inspect perimeter barriers and clear street-level trash grates.",
            "Prepare emergency go-bags with waterproof document containers.",
            "Monitor live GreenLens rolling hydrographs for peak intensity arrival."
        ]
    elif rain_24h >= 15.0 or surcharge_ratio >= 0.5 or overtopping_prob >= 40:
        severity = "MODERATE"
        should_alert = True
        title = "🟡 MODERATE FLOOD RISK: Rain Accumulation Ahead"
        message = f"Significant rainfall ({rain_24h:.1f} mm in 24h) forecasted. Check local culverts and ensure domestic drainage channels are free of debris."
        actions = [
            "Clear domestic gutter downspouts and plastic litter before heavy rain starts.",
            "Use GreenLens AI camera to report newly choked culvert blocks to municipal dispatch.",
            "Move vehicles parked near drainage ditches to higher ground."
        ]
    elif rain_prob_24h >= 80 or rain_24h >= 5.0 or peak_hourly >= 2.0:
        severity = "INFO"
        should_alert = True
        title = "ℹ️ Rain Advisory: Prepare Drainage Routes"
        message = f"Rain forecast detected for your catchment ({rain_prob_24h}% chance). Ensure nearby street gutters and grates are clear of refuse."
        actions = [
            "Ensure neighborhood storm grates are free of plastic debris.",
            "Keep an eye on regional weather updates."
        ]
    else:
        severity = "NONE"
        should_alert = False
        title = "✅ Normal Drainage Conditions"
        message = "Drainage capacity is operating within safe conveyance parameters."
        actions = [
            "Maintain clean culverts to preserve unhindered municipal flow."
        ]

    from datetime import datetime, timezone
    return {
        "alert_severity": severity,
        "should_alert": should_alert,
        "title": title,
        "message": message,
        "key_metrics": key_metrics,
        "time_to_overflow_hours": time_to_overflow,
        "safe_actions": actions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

