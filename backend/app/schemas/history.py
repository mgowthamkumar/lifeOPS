from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    entity_type: str
    entity_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime

class ActivityStatsResponse(BaseModel):
    total_events: int
    by_entity_type: Dict[str, int]
    by_action: Dict[str, int]
