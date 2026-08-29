import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "03a05cb89e344fcb8ce164434252406")
    WEATHER_API_BASE_URL: str = os.getenv("WEATHER_API_BASE_URL", "http://api.weatherapi.com/v1")
    PORT: int = int(os.getenv("PORT", "8000"))
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure upload dir exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
