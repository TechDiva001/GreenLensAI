from typing import Dict, Any, Optional
from core.security import supabase_client
import logging

logger = logging.getLogger("GreenLensAI_V2")

# create_report has been removed since the frontend handles insertions for strict RLS.

def verify_report_cleanup(ai_report_id: str, verified: bool) -> bool:
    if not supabase_client:
        logger.warning("Supabase client is not initialized; skipping report status update.")
        return False
    try:
        status = "RESOLVED" if verified else "REJECTED"
        supabase_client.table("reports").update({"status": status}).eq("ai_report_id", ai_report_id).execute()
        return True
    except Exception as e:
        logger.exception("Failed to update report cleanup status")
        return False
