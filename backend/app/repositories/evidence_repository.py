from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.evidence_analysis import Evidence, EvidenceInvestigation, ActivityLog
from app.repositories.base import BaseRepository

class EvidenceInvestigationRepository(BaseRepository[EvidenceInvestigation]):
    def __init__(self, db: Session):
        super().__init__(EvidenceInvestigation, db)

    def list_by_user(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        conflicts_only: bool = False,
        limit: int = 50,
    ) -> List[EvidenceInvestigation]:
        query = self.db.query(EvidenceInvestigation).filter(EvidenceInvestigation.user_id == user_id)
        if collection_id:
            query = query.filter(EvidenceInvestigation.collection_id == collection_id)
        if conflicts_only:
            query = query.filter(EvidenceInvestigation.conflict_detected == True)
        return query.order_by(EvidenceInvestigation.created_at.desc()).limit(limit).all()

    def get_by_id_and_user(self, investigation_id: str, user_id: str) -> Optional[EvidenceInvestigation]:
        return (
            self.db.query(EvidenceInvestigation)
            .filter(EvidenceInvestigation.id == investigation_id, EvidenceInvestigation.user_id == user_id)
            .first()
        )

class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, db: Session):
        super().__init__(Evidence, db)

    def list_by_document(self, document_id: str) -> List[Evidence]:
        return self.db.query(Evidence).filter(Evidence.document_id == document_id).all()

    def list_by_investigation(self, investigation_id: str) -> List[Evidence]:
        return self.db.query(Evidence).filter(Evidence.investigation_id == investigation_id).all()

    def list_by_user(self, user_id: str, limit: int = 50) -> List[Evidence]:
        return self.db.query(Evidence).filter(Evidence.user_id == user_id).order_by(Evidence.created_at.desc()).limit(limit).all()

class ActivityLogRepository(BaseRepository[ActivityLog]):
    def __init__(self, db: Session):
        super().__init__(ActivityLog, db)

    def log_activity(
        self,
        entity_type: str,
        action: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> ActivityLog:
        return self.create(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
        )

    def list_recent(self, user_id: Optional[str] = None, limit: int = 20) -> List[ActivityLog]:
        query = self.db.query(ActivityLog)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

    def filter_logs(
        self,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[ActivityLog]:
        query = self.db.query(ActivityLog)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if entity_type and entity_type.upper() != "ALL":
            query = query.filter(ActivityLog.entity_type == entity_type.upper())
        return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

    def clear_all(self, user_id: Optional[str] = None) -> int:
        query = self.db.query(ActivityLog)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        deleted = query.delete(synchronize_session=False)
        self.db.commit()
        return deleted

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        logs = self.list_recent(user_id=user_id, limit=500)
        by_entity: Dict[str, int] = {}
        by_action: Dict[str, int] = {}
        for l in logs:
            by_entity[l.entity_type] = by_entity.get(l.entity_type, 0) + 1
            by_action[l.action] = by_action.get(l.action, 0) + 1
        return {
            "total_events": len(logs),
            "by_entity_type": by_entity,
            "by_action": by_action,
        }

