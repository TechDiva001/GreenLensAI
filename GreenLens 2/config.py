import os

# API configuration
PORT = int(os.getenv("PORT", 8000))
HOST = "0.0.0.0"

# Gemini API Configurations
# Google AI Studio API Key (Free tier)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Directory configurations
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Local Model Configurations
YOLO_MODEL_NAME = "yolov8n.pt"

# Open-Meteo Weather API Base URL
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Default GPS Coordinates (Accra, Ghana)
DEFAULT_LAT = 5.6037
DEFAULT_LON = -0.1870

# Image similarity threshold for dHash (Lower means more similar, 0-64 scale)
DUPLICATE_HASH_THRESHOLD = 10

# GPS distance threshold for duplicates (in meters)
DUPLICATE_DISTANCE_THRESHOLD_METERS = 50.0

# Time threshold for duplicates (in hours)
DUPLICATE_TIME_THRESHOLD_HOURS = 24.0

# Risk formula weights (must sum to 1.0)
WEIGHT_BLOCKAGE = 0.35
WEIGHT_RAINFALL = 0.30
WEIGHT_HISTORICAL = 0.15
WEIGHT_CAPACITY = 0.10      # Restore capacity contribution
WEIGHT_ACCUMULATION = 0.05  # Waste accumulation contribution
WEIGHT_LOCATION = 0.05      # Proximity/Location contribution

# Mock Database of known drainage infrastructure segments in Accra (for Proximity Calculation)
KNOWN_DRAINAGE_SEGMENTS = [
    {"segment_id": "D-101", "name": "Accra Mall Gutter East", "latitude": 5.6150, "longitude": -0.1730, "capacity_restored": 80},
    {"segment_id": "D-102", "name": "Airport Residential Drain", "latitude": 5.6080, "longitude": -0.1800, "capacity_restored": 95},
    {"segment_id": "D-103", "name": "East Legon Main Culvert", "latitude": 5.6320, "longitude": -0.1550, "capacity_restored": 60},
    {"segment_id": "D-104", "name": "Osu Oxford Street Storm Drain", "latitude": 5.5600, "longitude": -0.1820, "capacity_restored": 85},
    {"segment_id": "D-105", "name": "Kaneshie Market Open Gutter", "latitude": 5.5720, "longitude": -0.2290, "capacity_restored": 50},
    {"segment_id": "D-106", "name": "Ablemkpe Culvert System", "latitude": 5.6020, "longitude": -0.2080, "capacity_restored": 70}
]
