from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.schemas.history import ActivityLogResponse, ActivityStatsResponse

router = APIRouter(prefix="/history", tags=["history"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

@router.get("", response_model=List[ActivityLogResponse], summary="List activity history events")
def list_history(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (TASK, GOAL, DECISION, DOCUMENT, SCENARIO, EVIDENCE)"),
    limit: int = Query(50, ge=1, le=200, description="Number of events to retrieve"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    repo = ActivityLogRepository(db)
    return repo.filter_logs(user_id=user_id, entity_type=entity_type, limit=limit)

@router.get("/stats", response_model=ActivityStatsResponse, summary="Get activity history telemetry statistics")
def get_history_stats(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    repo = ActivityLogRepository(db)
    stats = repo.get_stats(user_id=user_id)
    return ActivityStatsResponse(
        total_events=stats["total_events"],
        by_entity_type=stats["by_entity_type"],
        by_action=stats["by_action"],
    )

@router.delete("", summary="Clear user activity history")
def clear_history(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    repo = ActivityLogRepository(db)
    deleted = repo.clear_all(user_id=user_id)
    return {"message": f"Cleared {deleted} activity history logs", "deleted_count": deleted}
