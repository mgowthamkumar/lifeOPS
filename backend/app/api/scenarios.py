import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioSimulationResponse,
)
from app.services.simulation_service import what_if_simulation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["What-If Scenarios"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

class SimulatePayload(BaseModel):
    baseline_scenario_id: Optional[str] = None
    parameter_overrides: Optional[Dict[str, Any]] = None

@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new What-If simulation scenario with custom parameters
    (available time, deadlines, priorities, budget, durations, goals, constraints).
    Baseline reality remains completely unchanged.
    """
    try:
        scenario = what_if_simulation_service.create_scenario(
            db=db, user_id=user_id, data=payload
        )
        return ScenarioResponse.model_validate(scenario)
    except Exception as e:
        logger.exception(f"Error creating scenario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scenario: {str(e)}",
        )

@router.get("", response_model=List[ScenarioResponse])
def list_scenarios(
    decision_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List all scenarios (baseline and custom) for the current user.
    """
    scenarios = what_if_simulation_service.list_scenarios(
        db=db, user_id=user_id, decision_id=decision_id
    )
    return [ScenarioResponse.model_validate(s) for s in scenarios]

@router.get("/baseline", response_model=ScenarioResponse)
def get_baseline_scenario(
    decision_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get or initialize the user's default baseline scenario (e.g. 4 hours/day, standard reality).
    """
    baseline = what_if_simulation_service.get_or_create_default_baseline(
        db=db, user_id=user_id, decision_id=decision_id
    )
    return ScenarioResponse.model_validate(baseline)

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get scenario details and latest simulation comparison results.
    """
    scenario = what_if_simulation_service.get_scenario(db=db, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found.",
        )
    return ScenarioResponse.model_validate(scenario)

@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: str,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update scenario parameters or description.
    """
    scenario = what_if_simulation_service.update_scenario(
        db=db, scenario_id=scenario_id, data=payload
    )
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found.",
        )
    return ScenarioResponse.model_validate(scenario)

@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a What-If scenario.
    """
    success = what_if_simulation_service.delete_scenario(db=db, scenario_id=scenario_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found.",
        )
    return {"success": True, "message": f"Scenario '{scenario_id}' deleted successfully."}

@router.post("/{scenario_id}/simulate", response_model=ScenarioSimulationResponse)
def simulate_scenario(
    scenario_id: str,
    payload: Optional[SimulatePayload] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Re-runs RAG, priority analysis, decision analysis, and action plan for this scenario;
    Compares against baseline;
    Returns difference, reasons, evidence, and confidence;
    Persists simulation results independently. Baseline remains unchanged.
    """
    try:
        baseline_id = payload.baseline_scenario_id if payload else None
        overrides = payload.parameter_overrides if payload else None

        result = what_if_simulation_service.simulate(
            db=db,
            scenario_id=scenario_id,
            user_id=user_id,
            baseline_scenario_id=baseline_id,
            parameter_overrides=overrides,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error simulating scenario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute simulation: {str(e)}",
        )
