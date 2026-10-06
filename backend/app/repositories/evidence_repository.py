from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.evidence_analysis import Evidence, ActivityLog
from app.repositories.base import BaseRepository

class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, db: Session):
        super().__init__(Evidence, db)

    def list_by_document(self, document_id: str) -> List[Evidence]:
        return self.db.query(Evidence).filter(Evidence.document_id == document_id).all()

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
