import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.task_goal_repository import TaskRepository

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_what_if_simulation_2h_vs_4h(client: TestClient):
    uid = uuid.uuid4().hex[:6]

    # Clean up tasks for clean test isolation
    for t in client.get("/api/tasks").json():
        client.delete(f"/api/tasks/{t['id']}")

    # 1. Create a Strategic Goal
    goal_resp = client.post("/api/goals", json={
        "title": f"Launch Scalable Platform {uid}",
        "description": "Platform modern architecture and deployment",
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 40.0,
    })
    assert goal_resp.status_code == 201
    goal_id = goal_resp.json()["id"]

    # 2. Upload Document with Operational Guidance
    col_resp = client.post("/api/collections", json={
        "name": f"Operations Guidelines {uid}",
        "description": "Team operating principles and capacity constraints",
    })
    assert col_resp.status_code == 201
    col_id = col_resp.json()["id"]

    doc_text = (
        "Engineering Capacity Policy 2026: "
        "Standard operating capacity requires 4 hours daily focused allocation. "
        "Constraining available time to 2 hours per day forces deferral of secondary tasks "
        "and restricts daily throughput to high-urgency items only."
    )
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"capacity_policy_{uid}.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201

    # 3. Create 3 Tasks with distinct durations (Total: 90 + 60 + 45 = 195 minutes)
    now = datetime.now(timezone.utc)

    # Task 1: 90 mins, URGENT, CRITICAL Goal
    t1_resp = client.post("/api/tasks", json={
        "title": f"Database Migration Execution {uid}",
        "description": "Execute schema migration and data backfill",
        "deadline": (now + timedelta(hours=6)).isoformat(),
        "priority": "URGENT",
        "estimated_duration_minutes": 90,
        "status": "TODO",
        "goal_id": goal_id,
    })
    assert t1_resp.status_code == 201
    t1_id = t1_resp.json()["id"]

    # Task 2: 60 mins, HIGH priority
    t2_resp = client.post("/api/tasks", json={
        "title": f"API Gateway Auth Verification {uid}",
        "description": "Test JWT rotation and rate limiting",
        "deadline": (now + timedelta(days=2)).isoformat(),
        "priority": "HIGH",
        "estimated_duration_minutes": 60,
        "status": "TODO",
        "goal_id": goal_id,
    })
    assert t2_resp.status_code == 201
    t2_id = t2_resp.json()["id"]

    # Task 3: 45 mins, MEDIUM priority
    t3_resp = client.post("/api/tasks", json={
        "title": f"Telemetry Pipeline Cleanup {uid}",
        "description": "Prune outdated log channels",
        "deadline": (now + timedelta(days=5)).isoformat(),
        "priority": "MEDIUM",
        "estimated_duration_minutes": 45,
        "status": "TODO",
    })
    assert t3_resp.status_code == 201
    t3_id = t3_resp.json()["id"]

    # 4. Create Decision with Options
    decision_resp = client.post("/api/decisions", json={
        "title": f"Caching Tier Decision {uid}",
        "question": "Which cache architecture fits our latency and budget constraints?",
        "constraints": ["Budget under $500", "Zero downtime"],
        "goal_ids": [goal_id],
        "options": [
            {"title": "Redis Cluster", "effort_estimate": "MEDIUM"},
            {"title": "Serverless Edge", "effort_estimate": "HIGH"},
        ],
    })
    assert decision_resp.status_code == 201
    decision_id = decision_resp.json()["id"]

    # 5. Get / Establish Baseline Scenario (4 hours/day = 240 mins)
    baseline_resp = client.get(f"/api/scenarios/baseline?decision_id={decision_id}")
    assert baseline_resp.status_code == 200
    baseline_scenario = baseline_resp.json()
    baseline_id = baseline_scenario["id"]
    assert baseline_scenario["is_baseline"] is True
    assert baseline_scenario["parameters"]["available_time_minutes"] == 240

    # 6. Create Scenario B: "Crunch Mode (2 hours/day)" = 120 mins
    scenario_b_payload = {
        "name": f"Crunch Mode 2h/day {uid}",
        "description": "Simulating severe time restriction down to 2 hours (120 mins) daily.",
        "decision_id": decision_id,
        "is_baseline": False,
        "parameters": {
            "available_time_minutes": 120,
            "budget": 300.0,
            "constraints": ["Daily available time max 120 minutes", "Budget reduced to $300"],
            "deadline_shifts": {},
            "priority_overrides": {},
            "task_duration_multiplier": 1.0,
        },
    }
    create_b_resp = client.post("/api/scenarios", json=scenario_b_payload)
    assert create_b_resp.status_code == 201
    scenario_b = create_b_resp.json()
    scenario_b_id = scenario_b["id"]
    assert scenario_b["is_baseline"] is False
    assert scenario_b["parameters"]["available_time_minutes"] == 120

    # 7. Run What-If Simulation on Scenario B
    sim_resp = client.post(
        f"/api/scenarios/{scenario_b_id}/simulate",
        json={"baseline_scenario_id": baseline_id},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    # Validate simulation payload structure:
    assert sim_data["scenario_id"] == scenario_b_id
    assert sim_data["baseline_scenario_id"] == baseline_id
    assert "baseline" in sim_data
    assert "scenario" in sim_data
    assert "differences" in sim_data
    assert "reasons" in sim_data
    assert "evidence" in sim_data
    assert "confidence" in sim_data
    assert sim_data["confidence_level"] in ["HIGH", "MEDIUM", "LOW"]

    # Verify Baseline Outcome (4h = 240m):
    # Total tasks duration = 90 + 60 + 45 = 195m <= 240m.
    # Therefore, all 3 tasks are PLANNED in baseline, 0 deferred!
    baseline_out = sim_data["baseline"]
    assert baseline_out["available_time_minutes"] == 240
    assert baseline_out["planned_actions_count"] == 3
    assert baseline_out["deferred_actions_count"] == 0
    assert baseline_out["allocated_time_minutes"] == 195

    # Verify Scenario Outcome (2h = 120m):
    # Task 1 (90m) fits within 120m.
    # Task 2 (60m) would require 90 + 60 = 150m > 120m, so Task 2 and Task 3 are DEFERRED!
    scenario_out = sim_data["scenario"]
    assert scenario_out["available_time_minutes"] == 120
    assert scenario_out["planned_actions_count"] == 1
    assert scenario_out["deferred_actions_count"] == 2
    assert scenario_out["allocated_time_minutes"] == 90
    assert scenario_out["planned_actions"][0]["task_id"] == t1_id

    # Verify Differences:
    diff_cats = [d["category"] for d in sim_data["differences"]]
    assert "TIME_BUDGET" in diff_cats
    assert "ACTION_PLAN" in diff_cats

    time_diff = next(d for d in sim_data["differences"] if d["category"] == "TIME_BUDGET")
    assert "240 minutes" in str(time_diff["baseline_value"])
    assert "120 minutes" in str(time_diff["scenario_value"])
    assert "-120 min" in str(time_diff["difference"])

    action_diff = next(d for d in sim_data["differences"] if d["category"] == "ACTION_PLAN")
    assert "3 planned" in str(action_diff["baseline_value"])
    assert "1 planned" in str(action_diff["scenario_value"])

    # Verify Reasons:
    assert len(sim_data["reasons"]) >= 2
    assert any("120" in r for r in sim_data["reasons"])

    # Verify Evidence:
    assert len(sim_data["evidence"]) > 0

    # 8. CRITICAL: Verify Baseline Remains UNCHANGED
    with SessionLocal() as db_session:
        # Check actual database tasks: still unmodified
        db_tasks = TaskRepository(db_session).list_by_user(baseline_scenario["user_id"])
        db_t1 = next(t for t in db_tasks if t.id == t1_id)
        db_t2 = next(t for t in db_tasks if t.id == t2_id)
        db_t3 = next(t for t in db_tasks if t.id == t3_id)

        assert db_t1.status == "TODO"
        assert db_t1.estimated_duration_minutes == 90
        assert db_t2.status == "TODO"
        assert db_t2.estimated_duration_minutes == 60
        assert db_t3.status == "TODO"
        assert db_t3.estimated_duration_minutes == 45

        # Check baseline scenario record: parameters intact
        db_baseline = ScenarioRepository(db_session).get(baseline_id)
        assert db_baseline.is_baseline is True
        assert db_baseline.parameters["available_time_minutes"] == 240

    # 9. Verify BOTH Scenarios Persist Independently
    get_base_resp = client.get(f"/api/scenarios/{baseline_id}")
    assert get_base_resp.status_code == 200
    retrieved_base = get_base_resp.json()
    assert retrieved_base["parameters"]["available_time_minutes"] == 240
    assert retrieved_base["is_baseline"] is True

    get_scen_resp = client.get(f"/api/scenarios/{scenario_b_id}")
    assert get_scen_resp.status_code == 200
    retrieved_scen = get_scen_resp.json()
    assert retrieved_scen["parameters"]["available_time_minutes"] == 120
    assert retrieved_scen["is_baseline"] is False
    assert retrieved_scen["simulation_result"] is not None
    assert retrieved_scen["simulation_result"]["scenario_id"] == scenario_b_id

    # Check database directly in fresh connection
    with SessionLocal() as db_session:
        repo = ScenarioRepository(db_session)
        s_base = repo.get(baseline_id)
        s_b = repo.get(scenario_b_id)

        assert s_base is not None
        assert s_b is not None
        assert s_base.id != s_b.id
        assert s_base.parameters["available_time_minutes"] == 240
        assert s_b.parameters["available_time_minutes"] == 120
        assert s_b.simulation_result.get("scenario_id") == scenario_b_id
