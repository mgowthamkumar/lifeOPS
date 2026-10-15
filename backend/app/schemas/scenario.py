from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    decision_id: Optional[str] = None
    is_baseline: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    decision_id: Optional[str] = None

class SimulationComparisonItem(BaseModel):
    category: str  # TIME_BUDGET, ACTION_PLAN, PRIORITY, DECISION, FEASIBILITY
    title: str
    baseline_value: Any
    scenario_value: Any
    difference: str
    reason: str

class ScenarioSimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    scenario_name: str
    baseline_scenario_id: Optional[str] = None
    baseline: Dict[str, Any]
    scenario: Dict[str, Any]
    differences: List[SimulationComparisonItem] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.95
    confidence_level: str = "HIGH"
    created_at: datetime

class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    decision_id: Optional[str] = None
    name: str
    is_baseline: bool
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    simulation_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
