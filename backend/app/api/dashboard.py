from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.models.collection import Collection
from app.models.document import Document, DocumentChunk
from app.models.task_goal import Task, Goal
from app.models.decision import Decision
from app.models.decision import Scenario
from app.models.evidence_analysis import EvidenceInvestigation
from app.models.action_plan import ActionPlan
from app.repositories.evidence_repository import ActivityLogRepository
from app.schemas.dashboard import DashboardStatsResponse
from app.schemas.history import ActivityLogResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

@router.get("/stats", response_model=DashboardStatsResponse, summary="Get full aggregate system telemetry for Dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    # Collections & Documents & Chunks
    collections_count = db.query(Collection).filter(Collection.user_id == user_id).count()
    documents_count = (
        db.query(Document)
        .join(Collection, Document.collection_id == Collection.id)
        .filter(Collection.user_id == user_id)
        .count()
    )
    chunks_count = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Collection, Document.collection_id == Collection.id)
        .filter(Collection.user_id == user_id)
        .count()
    )

    # Tasks
    tasks_query = db.query(Task).filter(Task.user_id == user_id)
    tasks_total = tasks_query.count()
    tasks_completed = tasks_query.filter(Task.status == "COMPLETED").count()
    tasks_pending = tasks_total - tasks_completed
    tasks_urgent = tasks_query.filter(Task.priority == "URGENT", Task.status != "COMPLETED").count()

    # Goals
    goals_query = db.query(Goal).filter(Goal.user_id == user_id)
    goals_total = goals_query.count()
    goals_achieved = goals_query.filter(Goal.status == "ACHIEVED").count()
    goals_active = goals_total - goals_achieved
    avg_progress = db.query(func.avg(Goal.progress)).filter(Goal.user_id == user_id).scalar() or 0.0

    # Decisions
    decisions_query = db.query(Decision).filter(Decision.user_id == user_id)
    decisions_total = decisions_query.count()
    decisions_analyzed = decisions_query.filter(Decision.status.in_(["ANALYZED", "DECIDED"])).count()
    decisions_decided = decisions_query.filter(Decision.status == "DECIDED").count()

    # Scenarios
    scenarios_total = db.query(Scenario).filter(Scenario.user_id == user_id).count()

    # Evidence Investigations & Conflicts
    inv_query = db.query(EvidenceInvestigation).filter(EvidenceInvestigation.user_id == user_id)
    evidence_investigations_total = inv_query.count()
    conflicts_detected_total = inv_query.filter(EvidenceInvestigation.conflict_detected == True).count()

    # Latest Action Plan
    latest_plan = (
        db.query(ActionPlan)
        .filter(ActionPlan.user_id == user_id)
        .order_by(ActionPlan.created_at.desc())
        .first()
    )
    latest_summary = latest_plan.summary if latest_plan else None
    latest_time = latest_plan.created_at.isoformat() if latest_plan else None

    # Recent activities
    act_repo = ActivityLogRepository(db)
    recent_logs = act_repo.list_recent(user_id=user_id, limit=8)
    activity_items = [
        ActivityLogResponse(
            id=log.id,
            user_id=log.user_id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            details=log.details,
            created_at=log.created_at,
        )
        for log in recent_logs
    ]

    return DashboardStatsResponse(
        collections_count=collections_count,
        documents_count=documents_count,
        chunks_count=chunks_count,
        tasks_total=tasks_total,
        tasks_completed=tasks_completed,
        tasks_pending=tasks_pending,
        tasks_urgent=tasks_urgent,
        goals_total=goals_total,
        goals_active=goals_active,
        goals_achieved=goals_achieved,
        goals_average_progress=round(float(avg_progress), 1),
        decisions_total=decisions_total,
        decisions_analyzed=decisions_analyzed,
        decisions_decided=decisions_decided,
        scenarios_total=scenarios_total,
        evidence_investigations_total=evidence_investigations_total,
        conflicts_detected_total=conflicts_detected_total,
        latest_action_plan_summary=latest_summary,
        latest_action_plan_time=latest_time,
        recent_activities=activity_items,
        system_status="operational",
    )
