from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ActionPlanItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    task_id: Optional[str] = None
    goal_id: Optional[str] = None
    priority: int
    priority_label: str
    action: str
    reason: str
    estimated_time: str
    estimated_minutes: int
    evidence: str
    confidence: float
    confidence_level: str
    is_completed: bool

class ActionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    query: str
    summary: str
    total_estimated_minutes: int
    available_minutes_constraint: int
    user_context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    status: str
    items: List[ActionPlanItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class ActionPlanRequest(BaseModel):
    query: Optional[str] = "What should I do today?"
    available_minutes: Optional[int] = None
    focus_areas: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
