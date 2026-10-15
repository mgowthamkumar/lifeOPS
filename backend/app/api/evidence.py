from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.evidence import (
    EvidenceExploreRequest,
    EvidenceExploreResponse,
    EvidenceInvestigationSummary,
)
from app.services.evidence_service import evidence_explorer_service

router = APIRouter(prefix="/evidence", tags=["evidence"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

@router.post(
    "/explore",
    response_model=EvidenceExploreResponse,
    status_code=status.HTTP_200_OK,
    summary="Explore claim evidence and detect cross-source conflicts",
)
def explore_claim(
    request: EvidenceExploreRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Submits a claim to the Evidence Explorer.
    Retrieves grounded evidence chunks from ChromaDB, evaluates relevance, stance,
    confidence, uncertainty, and detects cross-source conflicts.
    Never fabricates citations.
    """
    try:
        return evidence_explorer_service.explore_claim(db=db, request=request, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence exploration failed: {str(e)}",
        )

@router.get(
    "",
    response_model=List[EvidenceInvestigationSummary],
    summary="List past evidence investigations",
)
def list_investigations(
    collection_id: Optional[str] = Query(None, description="Filter by collection"),
    conflicts_only: bool = Query(False, description="Filter only investigations with detected conflicts"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Lists past evidence investigations for the user."""
    return evidence_explorer_service.list_investigations(
        db=db,
        user_id=user_id,
        collection_id=collection_id,
        conflicts_only=conflicts_only,
    )

@router.get(
    "/conflicts",
    response_model=List[EvidenceInvestigationSummary],
    summary="List all investigations with detected conflicts",
)
def list_conflicts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Lists investigations where contradictory evidence was found across sources."""
    return evidence_explorer_service.list_investigations(
        db=db,
        user_id=user_id,
        conflicts_only=True,
    )

@router.get(
    "/{investigation_id}",
    response_model=EvidenceExploreResponse,
    summary="Get single evidence investigation details",
)
def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieves full details of a past evidence exploration."""
    res = evidence_explorer_service.get_investigation(db=db, investigation_id=investigation_id, user_id=user_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence investigation not found")
    return res

@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an evidence investigation record",
)
def delete_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Deletes an evidence investigation record."""
    success = evidence_explorer_service.delete_investigation(db=db, investigation_id=investigation_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence investigation not found")
    return {"message": "Evidence investigation deleted successfully"}
