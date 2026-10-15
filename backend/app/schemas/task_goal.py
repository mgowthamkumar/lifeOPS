from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Task Schemas ---

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    estimated_duration_minutes: int = Field(default=60, ge=1, description="Estimated duration in minutes")
    status: str = Field(default="TODO", description="TODO, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED")
    category: Optional[str] = Field(default="General", max_length=100)
    goal_id: Optional[str] = None
    document_ids: Optional[List[str]] = Field(default_factory=list)

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None
    category: Optional[str] = None
    goal_id: Optional[str] = None
    document_ids: Optional[List[str]] = None

class TaskDocumentRef(BaseModel):
    id: str
    filename: str
    file_type: str

class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str
    estimated_duration_minutes: int
    status: str
    category: Optional[str] = None
    goal_id: Optional[str] = None
    goal_title: Optional[str] = None
    documents: List[TaskDocumentRef] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

# --- Goal Schemas ---

class GoalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    status: str = Field(default="ACTIVE", description="ACTIVE, IN_PROGRESS, ACHIEVED, CANCELLED")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="0.0 to 100.0%")

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)

class GoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    importance: str
    status: str
    progress: float
    task_count: int = 0
    completed_task_count: int = 0
    created_at: datetime
    updated_at: datetime
