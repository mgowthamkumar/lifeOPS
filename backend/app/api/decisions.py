import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.decision import (
    DecisionCreate,
    DecisionUpdate,
    DecisionResponse,
    DecisionOptionCreate,
    DecisionOptionResponse,
    DecisionGoalRef,
    DecisionAnalysisResponse,
)
from app.services.decision_service import decision_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decisions", tags=["Decisions"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

def _to_decision_response(decision) -> DecisionResponse:
    goal_refs = [
        DecisionGoalRef(id=g.id, title=g.title, importance=g.importance)
        for g in (decision.goals or [])
    ]

    option_refs = [
        DecisionOptionResponse.model_validate(opt)
        for opt in (decision.options or [])
    ]

    latest_analysis = None
    if decision.latest_analysis:
        latest_analysis = DecisionAnalysisResponse.model_validate(decision.latest_analysis)

    return DecisionResponse(
        id=decision.id,
        user_id=decision.user_id,
        title=decision.title,
        question=decision.question,
        context_description=decision.context_description,
        deadline=decision.deadline,
        constraints=decision.constraints or [],
        status=decision.status,
        selected_option_id=decision.selected_option_id,
        goals=goal_refs,
        options=option_refs,
        latest_analysis=latest_analysis,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )

class SelectOptionPayload(BaseModel):
    option_id: str

@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create_decision(
    payload: DecisionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new strategic decision with question, context, linked goals,
    constraints, and candidate options.
    """
    try:
        decision = decision_service.create_decision(db=db, user_id=user_id, data=payload)
        return _to_decision_response(decision)
    except Exception as e:
        logger.exception(f"Error creating decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create decision: {str(e)}",
        )

@router.get("", response_model=List[DecisionResponse])
def list_decisions(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    List all decisions for the current user, optionally filtered by status (DRAFT, ANALYZED, DECIDED).
    """
    decisions = decision_service.list_decisions(db=db, user_id=user_id, status_filter=status_filter)
    return [_to_decision_response(d) for d in decisions]

@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get full details for a decision including options, linked goals, and latest analysis.
    """
    decision = decision_service.get_decision(db=db, decision_id=decision_id, user_id=user_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found.",
        )
    return _to_decision_response(decision)

@router.put("/{decision_id}", response_model=DecisionResponse)
def update_decision(
    decision_id: str,
    payload: DecisionUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update decision details, goals, or constraints.
    """
    decision = decision_service.update_decision(
        db=db, decision_id=decision_id, user_id=user_id, data=payload
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found.",
        )
    return _to_decision_response(decision)

@router.delete("/{decision_id}")
def delete_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a decision and all associated options and analysis records.
    """
    success = decision_service.delete_decision(db=db, decision_id=decision_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found.",
        )
    return {"success": True, "message": f"Decision '{decision_id}' deleted successfully."}

@router.post("/{decision_id}/options", response_model=DecisionOptionResponse, status_code=status.HTTP_201_CREATED)
def add_decision_option(
    decision_id: str,
    payload: DecisionOptionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Add a candidate option to a decision.
    """
    try:
        opt = decision_service.add_option(
            db=db, decision_id=decision_id, user_id=user_id, data=payload
        )
        return DecisionOptionResponse.model_validate(opt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error adding option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add option: {str(e)}",
        )

@router.delete("/{decision_id}/options/{option_id}")
def delete_decision_option(
    decision_id: str,
    option_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a candidate option from a decision.
    """
    success = decision_service.delete_option(
        db=db, decision_id=decision_id, option_id=option_id, user_id=user_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option '{option_id}' not found on decision '{decision_id}'.",
        )
    return {"success": True, "message": f"Option '{option_id}' deleted successfully."}

@router.post("/{decision_id}/analyze", response_model=DecisionAnalysisResponse)
def analyze_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Execute Decision Intelligence analysis:
    - Retrieve relevant document evidence across ChromaDB
    - Analyze each option against goals, constraints, effort, and evidence
    - Return match score, strengths, weaknesses, gaps, constraints, goal alignment, evidence, confidence, recommendations
    - Persist results in the database
    """
    try:
        analysis = decision_service.analyze_decision(
            db=db, decision_id=decision_id, user_id=user_id
        )
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error analyzing decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze decision: {str(e)}",
        )

@router.patch("/{decision_id}/select-option", response_model=DecisionResponse)
def select_decision_option(
    decision_id: str,
    payload: SelectOptionPayload,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Select an option to resolve the decision and set status to DECIDED.
    """
    try:
        decision = decision_service.select_option(
            db=db, decision_id=decision_id, option_id=payload.option_id, user_id=user_id
        )
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Decision '{decision_id}' not found.",
            )
        return _to_decision_response(decision)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error selecting option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select option: {str(e)}",
        )
