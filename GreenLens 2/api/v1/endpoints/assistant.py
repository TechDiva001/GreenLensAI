import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from schemas.report_schema import ChatRequest, ChatResponse, DailySummaryResponse
from services.assistant_service import chat_municipal_assistant, generate_daily_summary
from core.config import settings

logger = logging.getLogger("GreenLensAI_V2")
router = APIRouter()

# Default fallback incidents for assistant RAG context when DB is empty or unpopulated
SAMPLE_INCIDENTS: List[Dict[str, Any]] = [
    {
        "report_id": "GL-10452",
        "risk_score": 82.5,
        "risk_level": "CRITICAL",
        "blockage_percentage": 76,
        "drain_detected": True,
        "drainage_structure": "open gutter",
        "waste_type": "plastic",
        "rain_24h_mm": 18.5,
        "latitude": 5.6152,
        "longitude": -0.1731,
        "location_name": "Accra Mall Gutter East"
    },
    {
        "report_id": "GL-10453",
        "risk_score": 64.0,
        "risk_level": "HIGH",
        "blockage_percentage": 55,
        "drain_detected": True,
        "drainage_structure": "concrete channel",
        "waste_type": "mixed",
        "rain_24h_mm": 12.0,
        "latitude": 5.5721,
        "longitude": -0.2292,
        "location_name": "Kaneshie Market Drain"
    }
]

def fetch_active_reports() -> List[Dict[str, Any]]:
    """
    Fetches active reports from Supabase if credentials are provided,
    otherwise returns recent/cached reports.
    """
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            res = supabase.from_("reports").select("*, ai_risk_assessments(*)").limit(20).execute()
            if res.data:
                reports = []
                for item in res.data:
                    ai = item.get("ai_risk_assessments", {}) or {}
                    reports.append({
                        "report_id": item.get("ai_report_id") or str(item.get("id")),
                        "risk_score": ai.get("overall_risk_score", 50.0),
                        "risk_level": ai.get("risk_level", "MODERATE"),
                        "blockage_percentage": ai.get("waste_risk_score", 40),
                        "drain_detected": True,
                        "drainage_structure": "open gutter",
                        "waste_type": item.get("title", "mixed"),
                        "rain_24h_mm": 10.0,
                        "latitude": item.get("latitude", 5.6037),
                        "longitude": item.get("longitude", -0.1870),
                        "location_name": item.get("address", "Accra")
                    })
                if reports:
                    return reports
        except Exception as e:
            logger.warning(f"Could not load reports from Supabase for assistant context: {e}")

    return SAMPLE_INCIDENTS

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(req: ChatRequest):
    """
    Municipal AI conversational assistant with RAG grounding over active environmental reports.
    """
    try:
        query = req.query.strip()
        if not query:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")
            
        reports = fetch_active_reports()
        reply = chat_municipal_assistant(query, reports)
        
        sources = [f"Report {r['report_id']}" for r in reports[:3]]
        return ChatResponse(response=reply, sources=sources)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in municipal assistant chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant error: {str(e)}"
        )

@router.get("/daily-summary", response_model=DailySummaryResponse)
async def get_daily_summary():
    """
    Generates an automated daily summary of active drainage and waste incidents for municipal teams.
    """
    try:
        reports = fetch_active_reports()
        summary_text = generate_daily_summary(reports)
        
        critical_count = sum(1 for r in reports if r.get("risk_level") == "CRITICAL")
        high_count = sum(1 for r in reports if r.get("risk_level") == "HIGH")
        
        return DailySummaryResponse(
            summary=summary_text,
            timestamp=datetime.utcnow().isoformat(),
            report_count=len(reports),
            critical_count=critical_count,
            high_count=high_count
        )
    except Exception as e:
        logger.exception("Error generating daily summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary error: {str(e)}"
        )
