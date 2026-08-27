import logging
from typing import List, Dict, Any
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def generate_daily_summary(reports: List[Dict[str, Any]]) -> str:
    """
    Summarizes operational data (AI Function #22).
    Generates a daily summary using Gemini API or a rule-based template fallback.
    """
    total_count = len(reports)
    drain_count = sum(1 for r in reports if r.get("drain_detected", False))
    critical_count = sum(1 for r in reports if r.get("risk_level") == "CRITICAL")
    high_count = sum(1 for r in reports if r.get("risk_level") == "HIGH")
    
    # Get highest priority report
    highest_priority_name = "N/A"
    if total_count > 0:
        sorted_reports = sorted(reports, key=lambda x: x.get("risk_score", 0.0), reverse=True)
        highest_report = sorted_reports[0]
        highest_priority_name = f"Report {highest_report.get('report_id')} ({highest_report.get('risk_level')} risk)"

    # If Gemini is configured, use it for writing a beautiful daily overview
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = (
                f"You are the GreenLens AI Municipal Assistant. Write a concise daily summary for municipal officers based on this data:\n"
                f"- Total reports received: {total_count}\n"
                f"- Drainage-related reports: {drain_count}\n"
                f"- Critical risk locations: {critical_count}\n"
                f"- High risk locations: {high_count}\n"
                f"- Highest priority intervention: {highest_priority_name}\n"
                f"Keep it professional, bulleted, and less than 150 words."
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini in summary service: {e}")
            
    # Rule-based fallback
    return (
        f"Daily AI Summary:\n"
        f"- {total_count} reports were received today.\n"
        f"- {drain_count} were verified as drainage-related.\n"
        f"- {critical_count} locations are currently classified as CRITICAL flood risk.\n"
        f"- {high_count} locations are currently classified as HIGH flood risk.\n"
        f"- The highest-priority intervention site is {highest_priority_name}."
    )

def chat_municipal_assistant(query: str, reports: List[Dict[str, Any]]) -> str:
    """
    RAG-enabled Municipal AI Assistant chatbot (AI Function #21).
    Answers questions based on report database.
    """
    # Create simple context string of active incidents
    serialized_incidents = []
    for r in reports:
        serialized_incidents.append(
            f"Report ID: {r.get('report_id')}, Risk Score: {r.get('risk_score')}/100, "
            f"Risk Level: {r.get('risk_level')}, Blockage: {r.get('blockage_percentage')}%, "
            f"Structure: {r.get('drainage_structure')}, Type: {r.get('waste_type')}, "
            f"Rain sum 24h: {r.get('rain_24h_mm')}mm, Location coordinates: {r.get('latitude')}, {r.get('longitude')}"
        )
    context = "\n".join(serialized_incidents) if serialized_incidents else "No active environmental reports in database."
    
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = (
                f"You are the GreenLens Municipal Assistant, a natural-language interface to the GreenLens Digital Twin.\n"
                f"Answer the user's question using the system database context below. If the answer is not in the context, use general knowledge but clearly state that it is outside the live report database.\n\n"
                f"Context Database:\n{context}\n\n"
                f"User Question: {query}\n"
                f"Answer:"
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini in chat assistant: {e}")
            
    # Rule-based fallback RAG engine
    query_lower = query.lower()
    if "highest flood risk" in query_lower or "critical" in query_lower:
        critical_reports = [r.get("report_id") for r in reports if r.get("risk_level") == "CRITICAL"]
        if critical_reports:
            return f"The reports with the highest flood risk are: {', '.join(critical_reports)}. These areas require immediate action."
        else:
            return "There are currently no locations flagged as critical flood risk."
            
    if "blockage" in query_lower:
        blockages = [f"{r.get('report_id')}: {r.get('blockage_percentage')}%" for r in reports if r.get("blockage_percentage", 0) > 0]
        if blockages:
            return f"Active drain blockages: {', '.join(blockages)}."
        else:
            return "No active blockages reported in the database."
            
    return (
        f"I am running in offline fallback mode. "
        f"Active reports database lists {len(reports)} total entries. "
        f"Please set your GEMINI_API_KEY to enable full conversational intelligence."
    )
