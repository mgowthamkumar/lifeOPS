from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import TaskRepository, GoalRepository
from app.schemas.task_goal import TaskCreate, TaskUpdate, TaskResponse, TaskDocumentRef

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

def _to_task_response(task) -> TaskResponse:
    doc_refs = [
        TaskDocumentRef(id=d.id, filename=d.filename, file_type=d.file_type)
        for d in task.documents
    ] if task.documents else []

    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        priority=task.priority,
        estimated_duration_minutes=task.estimated_duration_minutes,
        status=task.status,
        category=task.category,
        goal_id=task.goal_id,
        goal_title=task.goal.title if task.goal else None,
        documents=doc_refs,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )

@router.get("", response_model=List[TaskResponse])
def list_tasks(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    goal_id: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[TaskResponse]:
    """Retrieves all tasks for the user, with optional filters."""
    repo = TaskRepository(db)
    tasks = repo.list_by_user(
        user_id=user_id,
        status=status_filter,
        priority=priority_filter,
        goal_id=goal_id,
        category=category,
    )
    return [_to_task_response(t) for t in tasks]

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """Creates a new task with optional goal and document links."""
    task_repo = TaskRepository(db)
    goal_repo = GoalRepository(db)

    # Validate goal if provided
    if payload.goal_id:
        goal = goal_repo.get(payload.goal_id)
        if not goal or goal.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated goal not found.")

    task = task_repo.create(
        user_id=user_id,
        goal_id=payload.goal_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        priority=payload.priority,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        status=payload.status,
        category=payload.category,
    )

    if payload.document_ids:
        task_repo.set_documents(task, payload.document_ids)

    # Recalculate goal progress if attached
    if task.goal_id:
        goal_repo.recalculate_progress(task.goal_id)

    db.refresh(task)
    return _to_task_response(task)

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """Retrieves a single task by ID."""
    task_repo = TaskRepository(db)
    task = task_repo.get(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return _to_task_response(task)

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """Updates an existing task."""
    task_repo = TaskRepository(db)
    goal_repo = GoalRepository(db)

    task = task_repo.get(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    old_goal_id = task.goal_id
    update_data = {
        k: v for k, v in payload.model_dump(exclude={"document_ids"}).items()
        if v is not None
    }

    # Validate goal if changed
    if "goal_id" in update_data and update_data["goal_id"]:
        goal = goal_repo.get(update_data["goal_id"])
        if not goal or goal.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated goal not found.")

    updated_task = task_repo.update(task_id, **update_data)

    if payload.document_ids is not None:
        task_repo.set_documents(updated_task, payload.document_ids)

    # Recalculate goal progress for old and new goals
    if old_goal_id:
        goal_repo.recalculate_progress(old_goal_id)
    if updated_task.goal_id and updated_task.goal_id != old_goal_id:
        goal_repo.recalculate_progress(updated_task.goal_id)

    db.refresh(updated_task)
    return _to_task_response(updated_task)

@router.patch("/{task_id}/complete", response_model=TaskResponse)
def toggle_task_complete(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """Toggles task status between COMPLETED and TODO."""
    task_repo = TaskRepository(db)
    goal_repo = GoalRepository(db)

    task = task_repo.get(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    new_status = "TODO" if task.status == "COMPLETED" else "COMPLETED"
    updated = task_repo.update(task_id, status=new_status)

    if updated.goal_id:
        goal_repo.recalculate_progress(updated.goal_id)

    db.refresh(updated)
    return _to_task_response(updated)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Deletes a task and recalculates its goal's progress."""
    task_repo = TaskRepository(db)
    goal_repo = GoalRepository(db)

    task = task_repo.get(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    goal_id = task.goal_id
    task_repo.delete(task_id)

    if goal_id:
        goal_repo.recalculate_progress(goal_id)
