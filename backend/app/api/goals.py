from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import GoalRepository
from app.schemas.task_goal import GoalCreate, GoalUpdate, GoalResponse

router = APIRouter(prefix="/goals", tags=["Goals"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

def _to_goal_response(goal) -> GoalResponse:
    total_tasks = len(goal.tasks)
    completed_tasks = sum(1 for t in goal.tasks if t.status == "COMPLETED")
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        description=goal.description,
        deadline=goal.deadline,
        importance=goal.importance,
        status=goal.status,
        progress=goal.progress,
        task_count=total_tasks,
        completed_task_count=completed_tasks,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )

@router.get("", response_model=List[GoalResponse])
def list_goals(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[GoalResponse]:
    """Retrieves all goals for the user, optionally filtered by status."""
    repo = GoalRepository(db)
    goals = repo.list_by_user(user_id, status=status_filter)
    return [_to_goal_response(g) for g in goals]

@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> GoalResponse:
    """Creates a new goal."""
    repo = GoalRepository(db)
    goal = repo.create(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        importance=payload.importance,
        status=payload.status,
        progress=payload.progress,
    )
    return _to_goal_response(goal)

@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> GoalResponse:
    """Retrieves a single goal by ID."""
    repo = GoalRepository(db)
    goal = repo.get(goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    return _to_goal_response(goal)

@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> GoalResponse:
    """Updates an existing goal."""
    repo = GoalRepository(db)
    goal = repo.get(goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = repo.update(goal_id, **update_data)
    return _to_goal_response(updated)

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Deletes a goal and its associated tasks."""
    repo = GoalRepository(db)
    goal = repo.get(goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    repo.delete(goal_id)
