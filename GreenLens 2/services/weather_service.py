import requests
import logging
from config import OPEN_METEO_BASE_URL

logger = logging.getLogger(__name__)

def get_weather_forecast(lat: float, lon: float):
    """
    Fetches the 48-hour rainfall forecast from Open-Meteo.
    Requires no API keys or payments.
    """
    try:
        # We request precipitation_sum and precipitation_probability for today and tomorrow (48h)
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["precipitation_sum", "precipitation_probability_max"],
            "timezone": "auto",
            "forecast_days": 2
        }
        response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        daily = data.get("daily", {})
        precip_sums = daily.get("precipitation_sum", [0.0, 0.0])
        precip_probs = daily.get("precipitation_probability_max", [0, 0])
        
        # Ensure values are clean
        rain_24h = float(precip_sums[0]) if (precip_sums and len(precip_sums) > 0 and precip_sums[0] is not None) else 0.0
        rain_48h = sum(float(x) for x in precip_sums if x is not None) if (precip_sums and len(precip_sums) > 1) else rain_24h
        
        prob_24h = int(precip_probs[0]) if (precip_probs and len(precip_probs) > 0 and precip_probs[0] is not None) else 0
        prob_48h = max(int(x) for x in precip_probs if x is not None) if (precip_probs and len(precip_probs) > 0) else prob_24h
        
        return {
            "rain_24h_mm": rain_24h,
            "rain_48h_mm": rain_48h,
            "rain_probability_24h": prob_24h,
            "rain_probability_48h": prob_48h
        }
    except Exception as e:
        logger.error(f"Error fetching weather from Open-Meteo: {e}")
        # Default fallback values for demo
        return {
            "rain_24h_mm": 5.0,
            "rain_48h_mm": 12.0,
            "rain_probability_24h": 40,
            "rain_probability_48h": 65
        }
