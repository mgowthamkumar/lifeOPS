from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task_goal import Goal, Task
from app.repositories.base import BaseRepository

class GoalRepository(BaseRepository[Goal]):
    def __init__(self, db: Session):
        super().__init__(Goal, db)

    def list_by_user(self, user_id: str, status: Optional[str] = None) -> List[Goal]:
        query = self.db.query(Goal).filter(Goal.user_id == user_id)
        if status:
            query = query.filter(Goal.status == status)
        return query.all()

class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def list_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        goal_id: Optional[str] = None,
    ) -> List[Task]:
        query = self.db.query(Task).filter(Task.user_id == user_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if goal_id:
            query = query.filter(Task.goal_id == goal_id)
        return query.all()
