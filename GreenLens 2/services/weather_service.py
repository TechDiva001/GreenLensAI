import requests
import logging
from typing import Dict, Any, List
from config import WEATHER_API_KEY, WEATHER_API_BASE_URL, OPEN_METEO_BASE_URL

logger = logging.getLogger(__name__)

def get_weather_forecast(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches weather conditions and 48-hour rainfall forecast from WeatherAPI (api.weatherapi.com).
    Falls back gracefully to Open-Meteo or defaults if network is offline.
    """
    # 1. Primary: WeatherAPI (api.weatherapi.com)
    if WEATHER_API_KEY:
        try:
            url = f"{WEATHER_API_BASE_URL}/forecast.json"
            params = {
                "key": WEATHER_API_KEY,
                "q": f"{lat},{lon}",
                "days": 3,
                "aqi": "no",
                "alerts": "yes"
            }
            response = requests.get(url, params=params, timeout=6)
            if response.status_code == 200:
                data = response.json()
                location_info = data.get("location", {})
                current_info = data.get("current", {})
                forecast_days = data.get("forecast", {}).get("forecastday", [])

                # Day 1 (24h) and Day 2 (48h)
                day1 = forecast_days[0] if len(forecast_days) > 0 else {}
                day2 = forecast_days[1] if len(forecast_days) > 1 else {}
                day3 = forecast_days[2] if len(forecast_days) > 2 else {}

                day1_day = day1.get("day", {})
                day2_day = day2.get("day", {})

                rain_24h_mm = float(day1_day.get("totalprecip_mm", 0.0) or 0.0)
                rain_day2_mm = float(day2_day.get("totalprecip_mm", 0.0) or 0.0)
                rain_48h_mm = round(rain_24h_mm + rain_day2_mm, 1)

                rain_prob_24h = int(day1_day.get("daily_chance_of_rain", 0) or 0)
                rain_prob_day2 = int(day2_day.get("daily_chance_of_rain", 0) or 0)
                rain_prob_48h = max(rain_prob_24h, rain_prob_day2)

                daily_cards: List[Dict[str, Any]] = []
                for fday in forecast_days:
                    d = fday.get("day", {})
                    cond = d.get("condition", {})
                    daily_cards.append({
                        "date": fday.get("date"),
                        "max_temp_c": d.get("maxtemp_c"),
                        "min_temp_c": d.get("mintemp_c"),
                        "avg_temp_c": d.get("avgtemp_c"),
                        "total_precip_mm": d.get("totalprecip_mm", 0.0),
                        "chance_of_rain": d.get("daily_chance_of_rain", 0),
                        "condition_text": cond.get("text", "Clear"),
                        "condition_icon": cond.get("icon", ""),
                    })

                current_cond = current_info.get("condition", {})
                return {
                    "source": "WeatherAPI",
                    "location": {
                        "name": location_info.get("name"),
                        "region": location_info.get("region"),
                        "country": location_info.get("country"),
                        "lat": location_info.get("lat", lat),
                        "lon": location_info.get("lon", lon)
                    },
                    "current": {
                        "temp_c": current_info.get("temp_c"),
                        "feelslike_c": current_info.get("feelslike_c"),
                        "humidity": current_info.get("humidity"),
                        "wind_kph": current_info.get("wind_kph"),
                        "precip_mm": current_info.get("precip_mm", 0.0),
                        "condition_text": current_cond.get("text", "Clear"),
                        "condition_icon": current_cond.get("icon", ""),
                        "is_day": current_info.get("is_day", 1)
                    },
                    "rain_24h_mm": rain_24h_mm,
                    "rain_48h_mm": rain_48h_mm,
                    "rain_probability_24h": rain_prob_24h,
                    "rain_probability_48h": rain_prob_48h,
                    "daily_forecast": daily_cards
                }
            else:
                logger.warning(f"WeatherAPI returned HTTP {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching weather from WeatherAPI: {e}")

    # 2. Secondary Fallback: Open-Meteo
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["precipitation_sum", "precipitation_probability_max", "temperature_2m_max", "temperature_2m_min"],
            "timezone": "auto",
            "forecast_days": 2
        }
        response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        daily = data.get("daily", {})
        precip_sums = daily.get("precipitation_sum", [0.0, 0.0])
        precip_probs = daily.get("precipitation_probability_max", [0, 0])
        
        rain_24h = float(precip_sums[0]) if (precip_sums and len(precip_sums) > 0 and precip_sums[0] is not None) else 0.0
        rain_48h = sum(float(x) for x in precip_sums if x is not None) if (precip_sums and len(precip_sums) > 1) else rain_24h
        prob_24h = int(precip_probs[0]) if (precip_probs and len(precip_probs) > 0 and precip_probs[0] is not None) else 0
        prob_48h = max(int(x) for x in precip_probs if x is not None) if (precip_probs and len(precip_probs) > 0) else prob_24h
        
        return {
            "source": "Open-Meteo",
            "location": {"name": "Accra", "region": "Greater Accra", "country": "Ghana", "lat": lat, "lon": lon},
            "current": {
                "temp_c": 28.0,
                "feelslike_c": 30.0,
                "humidity": 78,
                "wind_kph": 14.0,
                "precip_mm": 0.0,
                "condition_text": "Partly Cloudy",
                "condition_icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
                "is_day": 1
            },
            "rain_24h_mm": rain_24h,
            "rain_48h_mm": rain_48h,
            "rain_probability_24h": prob_24h,
            "rain_probability_48h": prob_48h,
            "daily_forecast": []
        }
    except Exception as e:
        logger.error(f"Error fetching weather fallback from Open-Meteo: {e}")
        # Default safety fallback
        return {
            "source": "Fallback Defaults",
            "location": {"name": "Accra", "region": "Greater Accra", "country": "Ghana", "lat": lat, "lon": lon},
            "current": {
                "temp_c": 28.0,
                "feelslike_c": 31.0,
                "humidity": 80,
                "wind_kph": 12.0,
                "precip_mm": 0.0,
                "condition_text": "Partly Cloudy",
                "condition_icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
                "is_day": 1
            },
            "rain_24h_mm": 4.5,
            "rain_48h_mm": 11.0,
            "rain_probability_24h": 45,
            "rain_probability_48h": 60,
            "daily_forecast": []
        }
