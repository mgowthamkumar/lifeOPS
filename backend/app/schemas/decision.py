from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DecisionOptionCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    effort_estimate: Optional[str] = None

class DecisionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_id: str
    title: str
    description: Optional[str] = None
    match_score: Optional[float] = None
    effort_estimate: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DecisionGoalRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    importance: str

class DecisionCreate(BaseModel):
    title: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    context_description: Optional[str] = None
    deadline: Optional[datetime] = None
    constraints: List[str] = Field(default_factory=list)
    goal_ids: List[str] = Field(default_factory=list)
    options: List[DecisionOptionCreate] = Field(default_factory=list)

class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    question: Optional[str] = None
    context_description: Optional[str] = None
    deadline: Optional[datetime] = None
    constraints: Optional[List[str]] = None
    goal_ids: Optional[List[str]] = None
    status: Optional[str] = None
    selected_option_id: Optional[str] = None

class OptionAnalysisItem(BaseModel):
    option_id: str
    option_title: str
    match: float  # 0.0 to 100.0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    goal_alignment: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.9  # 0.0 to 1.0
    recommendation: str

class DecisionAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: str
    recommendation: str
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning_summary: str
    top_option_id: Optional[str] = None
    options_analysis: List[OptionAnalysisItem] = Field(default_factory=list)
    created_at: datetime

class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    question: str
    context_description: Optional[str] = None
    deadline: Optional[datetime] = None
    constraints: List[str] = Field(default_factory=list)
    status: str
    selected_option_id: Optional[str] = None
    goals: List[DecisionGoalRef] = Field(default_factory=list)
    options: List[DecisionOptionResponse] = Field(default_factory=list)
    latest_analysis: Optional[DecisionAnalysisResponse] = None
    created_at: datetime
    updated_at: datetime
