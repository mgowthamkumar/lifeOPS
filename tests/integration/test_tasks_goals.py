import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import SessionLocal
from app.models.task_goal import Goal, Task
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import GoalRepository, TaskRepository

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_goal_crud_and_progress_flow(client: TestClient):
    # 1. Create Goal
    goal_payload = {
        "title": "Master Full-Stack AI Engineering",
        "description": "Build end-to-end RAG systems with FastAPI and React",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 0.0,
    }
    create_resp = client.post("/api/goals", json=goal_payload)
    assert create_resp.status_code == 201
    goal = create_resp.json()
    goal_id = goal["id"]
    assert goal["title"] == "Master Full-Stack AI Engineering"
    assert goal["importance"] == "CRITICAL"
    assert goal["progress"] == 0.0

    # 2. Edit Goal
    update_resp = client.put(f"/api/goals/{goal_id}", json={
        "importance": "HIGH",
        "description": "Updated goal description with milestone metrics",
    })
    assert update_resp.status_code == 200
    updated_goal = update_resp.json()
    assert updated_goal["importance"] == "HIGH"
    assert "milestone metrics" in updated_goal["description"]

    # 3. List Goals
    list_resp = client.get("/api/goals")
    assert list_resp.status_code == 200
    all_goals = list_resp.json()
    assert any(g["id"] == goal_id for g in all_goals)

    # 4. Delete Goal
    del_resp = client.delete(f"/api/goals/{goal_id}")
    assert del_resp.status_code == 204

    # Verify not found
    get_resp = client.get(f"/api/goals/{goal_id}")
    assert get_resp.status_code == 404

def test_task_crud_with_goal_and_documents(client: TestClient):
    # 1. Create a Goal
    goal_resp = client.post("/api/goals", json={
        "title": "Ship LifeOps Production Engine",
        "importance": "HIGH",
        "status": "ACTIVE",
    })
    assert goal_resp.status_code == 201
    goal_id = goal_resp.json()["id"]

    # 2. Create a Collection and Document to link
    col_resp = client.post("/api/collections", json={
        "name": "Task Docs Col",
        "description": "Specs and manuals",
    })
    col_id = col_resp.json()["id"]

    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("rag_spec.txt", b"RAG Architectural Specification and SLA targets.", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    # 3. Create Task linked to Goal and Document
    task_payload = {
        "title": "Implement RAG vector indexing test suite",
        "description": "Write pytest coverage for vector storage and ChromaDB cosine queries",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "priority": "HIGH",
        "estimated_duration_minutes": 120,
        "status": "TODO",
        "category": "Engineering",
        "goal_id": goal_id,
        "document_ids": [doc_id],
    }
    create_task_resp = client.post("/api/tasks", json=task_payload)
    assert create_task_resp.status_code == 201
    task = create_task_resp.json()
    task_id = task["id"]
    assert task["title"] == "Implement RAG vector indexing test suite"
    assert task["priority"] == "HIGH"
    assert task["estimated_duration_minutes"] == 120
    assert task["goal_id"] == goal_id
    assert task["goal_title"] == "Ship LifeOps Production Engine"
    assert len(task["documents"]) == 1
    assert task["documents"][0]["id"] == doc_id
    assert task["documents"][0]["filename"] == "rag_spec.txt"

    # 4. Edit Task
    edit_resp = client.put(f"/api/tasks/{task_id}", json={
        "priority": "URGENT",
        "estimated_duration_minutes": 90,
    })
    assert edit_resp.status_code == 200
    assert edit_resp.json()["priority"] == "URGENT"
    assert edit_resp.json()["estimated_duration_minutes"] == 90

    # 5. Complete Task (PATCH /complete)
    complete_resp = client.patch(f"/api/tasks/{task_id}/complete")
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"

    # Verify Goal Progress was automatically updated
    updated_goal_resp = client.get(f"/api/goals/{goal_id}")
    assert updated_goal_resp.status_code == 200
    assert updated_goal_resp.json()["progress"] == 100.0
    assert updated_goal_resp.json()["completed_task_count"] == 1

    # 6. Delete Task
    del_task_resp = client.delete(f"/api/tasks/{task_id}")
    assert del_task_resp.status_code == 204

    # Verify task deleted
    assert client.get(f"/api/tasks/{task_id}").status_code == 404

    # Cleanup Goal and Collection
    client.delete(f"/api/goals/{goal_id}")
    client.delete(f"/api/collections/{col_id}")

def test_task_goal_persistence_across_restart():
    # 1. Connect to database and create User, Goal, and Task
    with SessionLocal() as session:
        user_id = UserRepository(session).get_or_create_default().id
        goal_repo = GoalRepository(session)
        task_repo = TaskRepository(session)

        persisted_goal = goal_repo.create(
            user_id=user_id,
            title="Restart Persistence Goal",
            description="Testing survival across engine restarts",
            importance="HIGH",
            status="ACTIVE",
            progress=50.0,
        )
        saved_goal_id = persisted_goal.id

        persisted_task = task_repo.create(
            user_id=user_id,
            goal_id=saved_goal_id,
            title="Restart Persistence Task",
            description="Should remain intact after DB session restart",
            priority="URGENT",
            estimated_duration_minutes=45,
            status="IN_PROGRESS",
            category="Testing",
        )
        saved_task_id = persisted_task.id

    # 2. Completely close sessions, simulate application restart by reading from fresh session
    with SessionLocal() as restart_session:
        goal_repo = GoalRepository(restart_session)
        task_repo = TaskRepository(restart_session)

        reloaded_goal = goal_repo.get(saved_goal_id)
        assert reloaded_goal is not None
        assert reloaded_goal.title == "Restart Persistence Goal"
        assert reloaded_goal.importance == "HIGH"
        assert reloaded_goal.progress == 50.0

        reloaded_task = task_repo.get(saved_task_id)
        assert reloaded_task is not None
        assert reloaded_task.title == "Restart Persistence Task"
        assert reloaded_task.priority == "URGENT"
        assert reloaded_task.estimated_duration_minutes == 45
        assert reloaded_task.status == "IN_PROGRESS"
        assert reloaded_task.goal_id == saved_goal_id

        # Cleanup
        task_repo.delete(saved_task_id)
        goal_repo.delete(saved_goal_id)
