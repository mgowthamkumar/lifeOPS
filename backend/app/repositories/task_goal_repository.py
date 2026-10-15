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

    def recalculate_progress(self, goal_id: str) -> Optional[Goal]:
        goal = self.get(goal_id)
        if not goal:
            return None
        total_tasks = len(goal.tasks)
        if total_tasks > 0:
            completed_tasks = sum(1 for t in goal.tasks if t.status == "COMPLETED")
            goal.progress = round((completed_tasks / total_tasks) * 100.0, 1)
            if goal.progress >= 100.0 and goal.status != "ACHIEVED":
                goal.status = "ACHIEVED"
            elif goal.progress < 100.0 and goal.status == "ACHIEVED":
                goal.status = "ACTIVE"
            self.db.commit()
            self.db.refresh(goal)
        return goal

class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def list_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        goal_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Task]:
        query = self.db.query(Task).filter(Task.user_id == user_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if goal_id:
            query = query.filter(Task.goal_id == goal_id)
        if category:
            query = query.filter(Task.category == category)
        return query.order_by(Task.created_at.desc()).all()

    def set_documents(self, task: Task, document_ids: List[str]) -> None:
        from app.models.document import Document
        if document_ids:
            docs = self.db.query(Document).filter(Document.id.in_(document_ids)).all()
            task.documents = docs
        else:
            task.documents = []
        self.db.commit()
        self.db.refresh(task)
