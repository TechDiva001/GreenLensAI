import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from core.security import supabase_client

logger = logging.getLogger("GreenLensAI_V2")

TABLE_NAME = "flood_event_history"

def insert_flood_event(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persists a flood prediction or ground-truth event to Supabase.
    Falls back to in-memory generation if Supabase client is unavailable.
    """
    if not supabase_client:
        logger.warning("Supabase client unavailable. Storing flood event in-memory only.")
        event_dict["id"] = int(datetime.now().timestamp() * 1000)
        event_dict["created_at"] = datetime.now(timezone.utc).isoformat()
        return event_dict

    try:
        # Clean nulls or ensure ISO formatted timestamps
        payload = {k: v for k, v in event_dict.items() if v is not None}
        if "event_timestamp" not in payload or not payload["event_timestamp"]:
            payload["event_timestamp"] = datetime.now(timezone.utc).isoformat()

        res = supabase_client.table(TABLE_NAME).insert(payload).execute()
        if res.data and len(res.data) > 0:
            logger.info(f"Persisted flood event to Supabase table '{TABLE_NAME}', id={res.data[0].get('id')}")
            return res.data[0]
        return payload
    except Exception as e:
        logger.error(f"Failed to persist flood event to Supabase: {e}. Falling back to in-memory event.")
        event_dict["id"] = int(datetime.now().timestamp() * 1000)
        event_dict["created_at"] = datetime.now(timezone.utc).isoformat()
        return event_dict

def query_flood_events(
    catchment: str,
    severity: Optional[str] = None,
    limit: int = 20
) -> Optional[List[Dict[str, Any]]]:
    """
    Queries archived flood events from Supabase filtered by catchment and severity.
    Returns None if Supabase is unavailable or table does not exist.
    """
    if not supabase_client:
        return None

    try:
        query = supabase_client.table(TABLE_NAME).select("*")
        if catchment:
            query = query.ilike("catchment_name", f"%{catchment}%")
        if severity:
            query = query.eq("severity", severity.upper())
            
        res = query.order("event_timestamp", desc=True).limit(limit).execute()
        if res.data is not None:
            return res.data
        return None
    except Exception as e:
        logger.warning(f"Failed to query Supabase '{TABLE_NAME}' table: {e}. Falling back to sample baseline.")
        return None
