import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.action_plan_repository import ActionPlanRepository

import uuid

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_full_action_planner_pipeline(client: TestClient):
    uid = uuid.uuid4().hex[:6]
    # Clean up any leftover tasks from previous runs
    for t in client.get("/api/tasks").json():
        client.delete(f"/api/tasks/{t['id']}")
    # 1. Create a Goal with CRITICAL importance
    goal_resp = client.post("/api/goals", json={
        "title": f"Achieve AI System Launch {uid}",
        "description": "Production readiness and deployment targets",
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 25.0,
    })
    assert goal_resp.status_code == 201
    goal = goal_resp.json()
    goal_id = goal["id"]

    # 2. Create a Collection and Upload an actual Document with Launch Specs
    col_resp = client.post("/api/collections", json={
        "name": f"Launch Standards Collection {uid}",
        "description": "System readiness documents",
    })
    assert col_resp.status_code == 201
    col_id = col_resp.json()["id"]

    doc_text = "Critical Launch Requirement: The RAG service latency must remain under 200ms and all security authorization tokens must be verified before production deployment."
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("launch_spec.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 3. Create Task 1: Due today, URGENT, CRITICAL goal, Linked to launch document
    now = datetime.now(timezone.utc)
    task1_resp = client.post("/api/tasks", json={
        "title": "Verify RAG Service Latency and Security Tokens",
        "description": "Measure ChromaDB latency and inspect auth headers per launch spec",
        "deadline": (now + timedelta(hours=6)).isoformat(),
        "priority": "URGENT",
        "estimated_duration_minutes": 60,
        "status": "TODO",
        "category": "Engineering",
        "goal_id": goal_id,
        "document_ids": [doc_id],
    })
    assert task1_resp.status_code == 201
    task1_id = task1_resp.json()["id"]

    # 4. Create Task 2: Due next week, LOW priority, Standalone
    task2_resp = client.post("/api/tasks", json={
        "title": "Team Retrospective Cleanup",
        "description": "Archive retrospective whiteboard notes",
        "deadline": (now + timedelta(days=7)).isoformat(),
        "priority": "LOW",
        "estimated_duration_minutes": 30,
        "status": "TODO",
        "category": "General",
        "document_ids": [],
    })
    assert task2_resp.status_code == 201
    task2_id = task2_resp.json()["id"]

    # 5. Create Task 3: Due tomorrow, HIGH priority, CRITICAL goal
    task3_resp = client.post("/api/tasks", json={
        "title": "Production Deployment Runbook Review",
        "description": "Walk through zero-downtime deployment steps with infrastructure lead",
        "deadline": (now + timedelta(hours=24)).isoformat(),
        "priority": "HIGH",
        "estimated_duration_minutes": 90,
        "status": "TODO",
        "category": "Engineering",
        "goal_id": goal_id,
        "document_ids": [],
    })
    assert task3_resp.status_code == 201
    task3_id = task3_resp.json()["id"]

    # 6. User asks: "What should I do today?" with a daily budget constraint of 240 minutes
    plan_resp = client.post("/api/action-planner/generate", json={
        "query": "What should I do today?",
        "available_minutes": 240,
        "focus_areas": ["Engineering"],
    })
    assert plan_resp.status_code == 201
    plan_data = plan_resp.json()
    plan_id = plan_data["id"]

    print("\n--- GENERATED ACTION PLAN ---")
    print(f"Summary: {plan_data['summary']}")
    print(f"Total Estimated Time: {plan_data['total_estimated_minutes']} mins")
    print(f"Items Count: {len(plan_data['items'])}")

    # 7. Verify Prioritization Quality & Grounding
    items = plan_data["items"]
    assert len(items) >= 2

    # Item #1 MUST be Task 1: due today + URGENT + CRITICAL goal + evidence
    item_1 = items[0]
    assert item_1["priority"] == 1
    assert item_1["task_id"] == task1_id
    assert "Verify RAG Service Latency" in item_1["action"]
    assert "URGENT" in item_1["priority_label"].upper()
    assert item_1["estimated_minutes"] == 60
    assert item_1["estimated_time"] in ["1h", "60 minutes", "1 hour"] or "60" in item_1["estimated_time"] or "1h" in item_1["estimated_time"]
    # Evidence must cite document or launch spec
    assert "launch_spec.txt" in item_1["evidence"] or "Doc" in item_1["evidence"] or "latency" in item_1["evidence"].lower()
    assert item_1["confidence"] >= 0.85
    assert item_1["confidence_level"] == "HIGH"

    # Item #2 should be Task 3 (HIGH priority, due tomorrow, CRITICAL goal)
    item_2 = items[1]
    assert item_2["priority"] == 2
    assert item_2["task_id"] == task3_id

    # 8. Verify Persistence via API
    latest_resp = client.get("/api/action-planner/latest")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["id"] == plan_id
    assert len(latest_data["items"]) == len(items)

    get_id_resp = client.get(f"/api/action-planner/{plan_id}")
    assert get_id_resp.status_code == 200
    assert get_id_resp.json()["id"] == plan_id

    history_resp = client.get("/api/action-planner/history")
    assert history_resp.status_code == 200
    assert any(p["id"] == plan_id for p in history_resp.json())

    # 9. Verify Persistence Across Database Session (Simulating Server Restart)
    with SessionLocal() as db_session:
        plan_repo = ActionPlanRepository(db_session)
        persisted_plan = plan_repo.get_with_items(plan_id)
        assert persisted_plan is not None
        assert persisted_plan.query == "What should I do today?"
        assert persisted_plan.total_estimated_minutes == plan_data["total_estimated_minutes"]
        assert len(persisted_plan.items) == len(items)
        assert persisted_plan.items[0].task_id == task1_id
        assert persisted_plan.items[0].priority == 1
        assert "launch_spec.txt" in persisted_plan.items[0].evidence or "Doc" in persisted_plan.items[0].evidence

    # 10. Clean up test records
    client.delete(f"/api/tasks/{task1_id}")
    client.delete(f"/api/tasks/{task2_id}")
    client.delete(f"/api/tasks/{task3_id}")
    client.delete(f"/api/goals/{goal_id}")
    client.delete(f"/api/collections/{col_id}")
