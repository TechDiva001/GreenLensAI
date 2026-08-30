import requests
import logging
from typing import Dict, Any, List
from datetime import datetime
from config import OPEN_METEO_BASE_URL, WEATHER_API_KEY, WEATHER_API_BASE_URL, DEFAULT_LAT, DEFAULT_LON, DEFAULT_SURCHARGE_THRESHOLD_MM_H

logger = logging.getLogger(__name__)

# WMO Weather Interpretation Codes (World Meteorological Organization standard)
WMO_CODES: Dict[int, tuple[str, str, str]] = {
    0: ("Clear sky", "☀️", "clear"),
    1: ("Mainly clear", "🌤️", "partly-cloudy"),
    2: ("Partly cloudy", "⛅", "partly-cloudy"),
    3: ("Overcast", "☁️", "cloudy"),
    45: ("Fog", "🌫️", "fog"),
    48: ("Depositing rime fog", "🌫️", "fog"),
    51: ("Light drizzle", "🌦️", "drizzle"),
    53: ("Moderate drizzle", "🌧️", "rain"),
    55: ("Dense drizzle", "🌧️", "heavy-rain"),
    56: ("Light freezing drizzle", "🌧️", "drizzle"),
    57: ("Dense freezing drizzle", "🌧️", "heavy-rain"),
    61: ("Slight rain", "🌦️", "rain"),
    63: ("Moderate rain", "🌧️", "rain"),
    65: ("Heavy rain", "⛈️", "heavy-rain"),
    66: ("Light freezing rain", "🌧️", "rain"),
    67: ("Heavy freezing rain", "⛈️", "heavy-rain"),
    71: ("Slight snow", "🌨️", "snow"),
    73: ("Moderate snow", "🌨️", "snow"),
    75: ("Heavy snow", "❄️", "snow"),
    77: ("Snow grains", "❄️", "snow"),
    80: ("Slight rain showers", "🌦️", "showers"),
    81: ("Moderate rain showers", "🌧️", "showers"),
    82: ("Violent rain showers", "⛈️", "storm"),
    85: ("Slight snow showers", "🌨️", "snow"),
    86: ("Heavy snow showers", "❄️", "snow"),
    95: ("Thunderstorm", "⚡⛈️", "thunderstorm"),
    96: ("Thunderstorm with slight hail", "⛈️", "thunderstorm"),
    99: ("Thunderstorm with heavy hail", "⛈️", "thunderstorm"),
}

def get_wmo_info(code: int) -> tuple[str, str, str]:
    return WMO_CODES.get(int(code), ("Variable Conditions", "⛅", "cloudy"))


def fetch_open_meteo_telemetry(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Dict[str, Any]:
    """
    Fetches real-time Open-Meteo meteorological telemetry, convective storm vectors,
    and 48-hour hourly rainfall hydrographs for municipal catchment areas.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
        "hourly": "precipitation_probability,precipitation,rain",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "forecast_days": 2
    }

    try:
        response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=7)
        if response.status_code == 200:
            data = response.json()
            current_raw = data.get("current", {})
            hourly_raw = data.get("hourly", {})
            daily_raw = data.get("daily", {})

            wmo_code = int(current_raw.get("weather_code", 0) or 0)
            cond_text, cond_icon, cond_slug = get_wmo_info(wmo_code)

            # Build 24h & 48h Hourly Hydrograph series
            raw_times = hourly_raw.get("time", [])[:48]
            raw_precips = hourly_raw.get("precipitation", [])[:48]
            raw_probs = hourly_raw.get("precipitation_probability", [])[:48]

            hydrograph: List[Dict[str, Any]] = []
            for t_str, p_val, pr_val in zip(raw_times, raw_precips, raw_probs):
                precip = float(p_val or 0.0)
                prob = int(pr_val or 0)
                
                # Format hour string (e.g., "14:00")
                if "T" in t_str:
                    hour_label = t_str.split("T")[1][:5]
                else:
                    hour_label = str(t_str)

                is_surcharge = precip >= DEFAULT_SURCHARGE_THRESHOLD_MM_H
                if precip >= 5.0:
                    intensity = "DANGER"
                elif precip >= DEFAULT_SURCHARGE_THRESHOLD_MM_H:
                    intensity = "WARNING"
                else:
                    intensity = "SAFE"

                hydrograph.append({
                    "time": t_str,
                    "hour": hour_label,
                    "precipitation_mm": round(precip, 2),
                    "rain_probability": prob,
                    "is_surcharge_threat": is_surcharge,
                    "runoff_intensity": intensity
                })

            precip_sums = daily_raw.get("precipitation_sum", [0.0, 0.0])
            rain_24h = float(precip_sums[0] or 0.0) if len(precip_sums) > 0 else 0.0
            rain_48h = float(sum([float(x or 0.0) for x in precip_sums])) if len(precip_sums) > 1 else rain_24h

            probs = daily_raw.get("precipitation_probability_max", [0, 0])
            prob_24h = int(probs[0] or 0) if len(probs) > 0 else 0
            prob_48h = max([int(x or 0) for x in probs]) if len(probs) > 0 else prob_24h

            # Resolve catchment location name
            is_winneba = abs(lat - 5.3435) < 0.1 and abs(lon - (-0.6256)) < 0.1
            loc_name = "Winneba Catchment" if is_winneba else "Municipal Catchment Basin"

            return {
                "source": "Open-Meteo v1",
                "is_fallback": False,
                "location": {
                    "name": loc_name,
                    "lat": lat,
                    "lon": lon,
                    "elevation": float(data.get("elevation", 15.0)),
                    "timezone": str(data.get("timezone", "UTC"))
                },
                "current": {
                    "temp_c": float(current_raw.get("temperature_2m", 28.0) or 28.0),
                    "feelslike_c": float(current_raw.get("temperature_2m", 28.0) or 28.0) + 2.0,
                    "humidity": int(current_raw.get("relative_humidity_2m", 78) or 78),
                    "wind_kph": float(current_raw.get("wind_speed_10m", 12.0) or 12.0),
                    "precipitation_mm": float(current_raw.get("precipitation", 0.0) or 0.0),
                    "weather_code": wmo_code,
                    "condition_text": cond_text,
                    "condition_icon": cond_icon,
                    "condition_slug": cond_slug,
                    "is_day": 1
                },
                "rain_24h_mm": round(rain_24h, 1),
                "rain_48h_mm": round(rain_48h, 1),
                "rain_probability_24h": prob_24h,
                "rain_probability_48h": prob_48h,
                "hydrograph": hydrograph
            }
        else:
            logger.warning(f"Open-Meteo returned HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Error connecting to Open-Meteo API: {e}")

    # Fallback to Coastal Climatology Baseline
    return _get_coastal_climatology_fallback(lat, lon)


def _get_coastal_climatology_fallback(lat: float, lon: float) -> Dict[str, Any]:
    """Realistic offline fallback based on West African coastal precipitation profiles."""
    current_hour = datetime.utcnow().hour
    mock_hydro = []
    for offset in range(24):
        target_h = (current_hour + offset) % 24
        # Afternoon convective storm modeling (14:00 - 17:00)
        if 14 <= target_h <= 17:
            p = 4.5
            prob = 75
            threat = True
            intensity = "WARNING"
        else:
            p = 0.2
            prob = 25
            threat = False
            intensity = "SAFE"

        mock_hydro.append({
            "time": f"{target_h:02d}:00",
            "hour": f"{target_h:02d}:00",
            "precipitation_mm": p,
            "rain_probability": prob,
            "is_surcharge_threat": threat,
            "runoff_intensity": intensity
        })

    is_winneba = abs(lat - 5.3435) < 0.1 and abs(lon - (-0.6256)) < 0.1
    loc_name = "Winneba Catchment" if is_winneba else "Municipal Catchment Basin"

    return {
        "source": "Open-Meteo (Climatology Fallback)",
        "is_fallback": True,
        "location": {
            "name": loc_name,
            "lat": lat,
            "lon": lon,
            "elevation": 15.0,
            "timezone": "GMT"
        },
        "current": {
            "temp_c": 28.5,
            "feelslike_c": 31.0,
            "humidity": 80,
            "wind_kph": 14.0,
            "precipitation_mm": 0.5,
            "weather_code": 61,
            "condition_text": "Scattered Showers",
            "condition_icon": "🌧️",
            "condition_slug": "rain",
            "is_day": 1
        },
        "rain_24h_mm": 16.5,
        "rain_48h_mm": 24.0,
        "rain_probability_24h": 70,
        "rain_probability_48h": 80,
        "hydrograph": mock_hydro
    }


def get_weather_forecast(lat: float, lon: float) -> Dict[str, Any]:
    """
    Unified forecast adapter returning Open-Meteo telemetry formatted for
    legacy GreenLens consumers and new hydrograph visualizers.
    """
    telemetry = fetch_open_meteo_telemetry(lat, lon)
    
    # Generate daily card summaries from hydrograph/telemetry
    daily_cards = [
        {
            "date": "Today",
            "max_temp_c": telemetry["current"]["temp_c"] + 2.0,
            "min_temp_c": telemetry["current"]["temp_c"] - 4.0,
            "avg_temp_c": telemetry["current"]["temp_c"],
            "total_precip_mm": telemetry["rain_24h_mm"],
            "chance_of_rain": telemetry["rain_probability_24h"],
            "condition_text": telemetry["current"]["condition_text"],
            "condition_icon": telemetry["current"]["condition_icon"],
        },
        {
            "date": "Tomorrow",
            "max_temp_c": telemetry["current"]["temp_c"] + 1.5,
            "min_temp_c": telemetry["current"]["temp_c"] - 4.5,
            "avg_temp_c": telemetry["current"]["temp_c"] - 1.0,
            "total_precip_mm": round(max(0.0, telemetry["rain_48h_mm"] - telemetry["rain_24h_mm"]), 1),
            "chance_of_rain": telemetry["rain_probability_48h"],
            "condition_text": "Patchy Showers",
            "condition_icon": "🌦️",
        }
    ]

    telemetry["daily_forecast"] = daily_cards
    return telemetry
