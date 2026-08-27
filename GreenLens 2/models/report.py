from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportModel(BaseModel):
    user_id: str
    municipality_id: Optional[int] = None
    title: str = "Issue Report"
    description: str = ""
    category_id: Optional[int] = None
    status: str = "Pending"
    latitude: float
    longitude: float
    address: Optional[str] = None
    accuracy: Optional[float] = None
    ai_report_id: str
