from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.models.action_plan import ActionPlan, ActionPlanItem
from app.repositories.base import BaseRepository

class ActionPlanRepository(BaseRepository[ActionPlan]):
    def __init__(self, db: Session):
        super().__init__(ActionPlan, db)

    def create_plan(
        self,
        user_id: str,
        query: str,
        summary: str,
        total_estimated_minutes: int,
        available_minutes_constraint: int,
        user_context_snapshot: Dict[str, Any],
        items_data: List[Dict[str, Any]],
        status: str = "ACTIVE",
    ) -> ActionPlan:
        plan = ActionPlan(
            user_id=user_id,
            query=query,
            summary=summary,
            total_estimated_minutes=total_estimated_minutes,
            available_minutes_constraint=available_minutes_constraint,
            user_context_snapshot=user_context_snapshot,
            status=status,
        )
        self.db.add(plan)
        self.db.flush()

        for item_dict in items_data:
            item = ActionPlanItem(
                plan_id=plan.id,
                task_id=item_dict.get("task_id"),
                goal_id=item_dict.get("goal_id"),
                priority=item_dict["priority"],
                priority_label=item_dict["priority_label"],
                action=item_dict["action"],
                reason=item_dict["reason"],
                estimated_time=item_dict["estimated_time"],
                estimated_minutes=item_dict.get("estimated_minutes", 0),
                evidence=item_dict["evidence"],
                confidence=float(item_dict.get("confidence", 0.9)),
                confidence_level=item_dict.get("confidence_level", "HIGH"),
                is_completed=item_dict.get("is_completed", False),
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_latest(self, user_id: str) -> Optional[ActionPlan]:
        return (
            self.db.query(ActionPlan)
            .options(joinedload(ActionPlan.items))
            .filter(ActionPlan.user_id == user_id)
            .order_by(ActionPlan.created_at.desc())
            .first()
        )

    def get_with_items(self, plan_id: str, user_id: Optional[str] = None) -> Optional[ActionPlan]:
        query = (
            self.db.query(ActionPlan)
            .options(joinedload(ActionPlan.items))
            .filter(ActionPlan.id == plan_id)
        )
        if user_id:
            query = query.filter(ActionPlan.user_id == user_id)
        return query.first()

    def list_plans(self, user_id: str, limit: int = 20) -> List[ActionPlan]:
        return (
            self.db.query(ActionPlan)
            .options(joinedload(ActionPlan.items))
            .filter(ActionPlan.user_id == user_id)
            .order_by(ActionPlan.created_at.desc())
            .limit(limit)
            .all()
        )
