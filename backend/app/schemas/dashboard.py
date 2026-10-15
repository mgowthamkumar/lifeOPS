from typing import Optional, List
from pydantic import BaseModel
from app.schemas.history import ActivityLogResponse

class DashboardStatsResponse(BaseModel):
    collections_count: int
    documents_count: int
    chunks_count: int
    tasks_total: int
    tasks_completed: int
    tasks_pending: int
    tasks_urgent: int
    goals_total: int
    goals_active: int
    goals_achieved: int
    goals_average_progress: float
    decisions_total: int
    decisions_analyzed: int
    decisions_decided: int
    scenarios_total: int
    evidence_investigations_total: int
    conflicts_detected_total: int
    latest_action_plan_summary: Optional[str] = None
    latest_action_plan_time: Optional[str] = None
    recent_activities: List[ActivityLogResponse] = []
    system_status: str = "operational"
