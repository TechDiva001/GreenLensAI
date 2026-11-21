import logging
from typing import Optional
from supabase import create_client, Client
from .config import settings

logger = logging.getLogger("GreenLensAI_V2")

def get_supabase_client() -> Optional[Client]:
    api_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
    if not settings.SUPABASE_URL or not api_key:
        logger.warning("SUPABASE_URL or API key not configured in environment. Running in offline/detached mode.")
        return None
    try:
        return create_client(settings.SUPABASE_URL, api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

supabase_client = get_supabase_client()
