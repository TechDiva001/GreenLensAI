from typing import Dict, Any, Optional
from core.security import supabase_client
import logging

logger = logging.getLogger("GreenLensAI_V2")

def create_report(report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert the AI analysis result into the Supabase reports table.
    """
    try:
        response = supabase_client.table("reports").insert({
            "user_id": report_data["user_id"],
            "municipality_id": report_data["municipality_id"],
            "title": "AI Auto-Generated Report",
            "description": report_data.get("description", ""),
            "status": "SUBMITTED" if report_data.get("fraud_flag") == False else "UNDER_REVIEW",
            "latitude": report_data["latitude"],
            "longitude": report_data["longitude"],
            "ai_report_id": report_data["report_id"]
        }).execute()
        
        if response.data:
            report = response.data[0]
            db_report_id = report["id"]
            
            # Insert media
            supabase_client.table("report_media").insert({
                "report_id": db_report_id,
                "media_type": "IMAGE",
                "file_url": report_data.get("image_url")
            }).execute()
            
            # Insert AI Risk Assessments
            supabase_client.table("ai_risk_assessments").insert({
                "report_id": db_report_id,
                "flood_risk_score": report_data.get("flood_risk_score", 0),
                "waste_risk_score": report_data.get("waste_risk_score", 0),
                "overall_risk_score": report_data.get("overall_risk_score", 0),
                "risk_level": report_data.get("risk_level", "LOW"),
                "reasoning": report_data.get("reasoning", "AI Assessment")
            }).execute()
            
            return report
        return None
    except Exception as e:
        logger.exception(f"Failed to insert report into Supabase: {str(e)}")
        return None

def verify_report_cleanup(ai_report_id: str, verified: bool) -> bool:
    try:
        status = "RESOLVED" if verified else "REJECTED"
        supabase_client.table("reports").update({"status": status}).eq("ai_report_id", ai_report_id).execute()
        return True
    except Exception as e:
        logger.exception("Failed to update report cleanup status")
        return False
