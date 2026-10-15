import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.action_plan_repository import ActionPlanRepository
from app.schemas.action_plan import (
    ActionPlanRequest,
    ActionPlanResponse,
    ActionPlanItemResponse,
)
from app.services.action_planner import action_planner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-planner", tags=["Action Planner"])

@router.post(
    "/generate",
    response_model=ActionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist a daily action plan",
)
def generate_action_plan(
    payload: ActionPlanRequest,
    db: Session = Depends(get_db),
):
    """
    Executes the ActionPlanner pipeline:
    Retrieves active tasks, parent goals, deadlines, user constraints, and RAG document evidence;
    Scores deterministically without random prioritization;
    Synthesizes grounded plan with Gemini;
    Persists plan and items in relational database.
    """
    try:
        user = UserRepository(db).get_or_create_default()
        plan = action_planner.plan_day(
            db=db,
            user_id=user.id,
            query=payload.query or "What should I do today?",
            available_minutes=payload.available_minutes,
            focus_areas=payload.focus_areas,
            custom_constraints=payload.constraints,
        )
        return plan
    except Exception as e:
        logger.exception(f"Error generating action plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate action plan: {str(e)}",
        )

@router.get(
    "/latest",
    response_model=ActionPlanResponse,
    summary="Get the most recent saved action plan",
)
def get_latest_action_plan(db: Session = Depends(get_db)):
    user = UserRepository(db).get_or_create_default()
    plan_repo = ActionPlanRepository(db)
    plan = plan_repo.get_latest(user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No action plans found. Generate a plan first.",
        )
    return plan

@router.get(
    "/history",
    response_model=List[ActionPlanResponse],
    summary="List past saved action plans",
)
def list_action_plans(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    user = UserRepository(db).get_or_create_default()
    plan_repo = ActionPlanRepository(db)
    return plan_repo.list_plans(user.id, limit=limit)

@router.get(
    "/{plan_id}",
    response_model=ActionPlanResponse,
    summary="Get a specific saved action plan by ID",
)
def get_action_plan_by_id(
    plan_id: str,
    db: Session = Depends(get_db),
):
    user = UserRepository(db).get_or_create_default()
    plan_repo = ActionPlanRepository(db)
    plan = plan_repo.get_with_items(plan_id, user_id=user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action plan not found.",
        )
    return plan
