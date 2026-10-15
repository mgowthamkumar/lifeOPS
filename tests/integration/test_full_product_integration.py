import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.task_goal_repository import TaskRepository, GoalRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.evidence_repository import EvidenceInvestigationRepository, ActivityLogRepository

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_full_product_integration_suite(client: TestClient):
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)

    # =========================================================================
    # 1. KNOWLEDGE BASE & DOCUMENTS: Upload, RAG, Update, & Vector Replacement
    # =========================================================================
    col_resp = client.post("/api/collections", json={
        "name": f"Core Knowledge {uid}",
        "description": "Integration test knowledge base"
    })
    assert col_resp.status_code == 201
    col_id = col_resp.json()["id"]

    v1_text = (
        f"Server Infrastructure Guide {uid}: "
        "Production database requires PostgreSQL 16 with pgvector extension. "
        "Minimum memory allocation is 8GB RAM with auto-scaling replicas."
    )
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"infra_guide_{uid}.txt", v1_text.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # RAG Question
    rag_resp = client.post("/api/rag/query", json={
        "collection_id": col_id,
        "question": "What is the memory allocation for production database?",
        "top_k": 3,
        "relevance_threshold": 0.10
    })
    assert rag_resp.status_code == 200
    rag_data = rag_resp.json()
    assert rag_data["has_sufficient_evidence"] is True
    assert rag_data["confidence_score"] > 0
    assert len(rag_data["sources"]) > 0
    assert "8GB" in rag_data["sources"][0]["content_snippet"]

    # Test Document Update (v2 replaces active version in ChromaDB)
    v2_text = (
        f"Server Infrastructure Guide {uid} Revised: "
        "Production database upgraded to 16GB RAM minimum with redundant read replicas. "
        "Zero downtime maintenance policy applies."
    )
    update_resp = client.put(
        f"/api/documents/{doc_id}/update",
        files={"file": (f"infra_guide_v2_{uid}.txt", v2_text.encode("utf-8"), "text/plain")},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["current_version"] == 2

    # Query RAG to verify updated knowledge is now retrieved
    rag_v2_resp = client.post("/api/rag/query", json={
        "collection_id": col_id,
        "question": "What is the upgraded memory allocation for production database?",
        "top_k": 3,
        "relevance_threshold": 0.10
    })
    assert rag_v2_resp.status_code == 200
    rag_v2_data = rag_v2_resp.json()
    assert any("16GB" in s["content_snippet"] for s in rag_v2_data["sources"])

    # =========================================================================
    # 2. GOALS & TASKS INTEGRATION
    # =========================================================================
    goal_resp = client.post("/api/goals", json={
        "title": f"Production Readiness {uid}",
        "description": "Ensure zero-downtime platform reliability",
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 25.0
    })
    assert goal_resp.status_code == 201
    goal_id = goal_resp.json()["id"]

    task_resp = client.post("/api/tasks", json={
        "title": f"Provision 16GB Cluster {uid}",
        "description": "Scale up production database nodes",
        "priority": "HIGH",
        "status": "TODO",
        "estimated_duration_minutes": 120,
        "goal_id": goal_id,
        "document_ids": [doc_id]
    })
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    # =========================================================================
    # 3. ACTION PLANNER GENERATION
    # =========================================================================
    plan_resp = client.post("/api/action-planner/generate", json={
        "query": "What should I do today?",
        "available_minutes": 240,
        "focus_areas": ["Production Readiness"],
    })
    assert plan_resp.status_code == 201
    plan_data = plan_resp.json()
    assert "items" in plan_data
    assert len(plan_data["items"]) > 0

    # =========================================================================
    # 4. DECISION INTELLIGENCE
    # =========================================================================
    dec_resp = client.post("/api/decisions", json={
        "title": f"Database Clustering Strategy {uid}",
        "question": "Which managed cluster tier should we deploy?",
        "context_description": "High-availability financial transactions",
        "constraints": ["Budget under $500/mo", "PostgreSQL compatibility"],
        "goal_ids": [goal_id],
        "options": [
            {
                "title": "Cloud SQL High Availability",
                "description": "Dual zone managed PostgreSQL with automated failover",
                "effort_estimate": "MEDIUM"
            },
            {
                "title": "Self-Managed VM Cluster",
                "description": "Custom Patroni clustering on Compute Engine VMs",
                "effort_estimate": "HIGH"
            }
        ]
    })
    assert dec_resp.status_code == 201
    dec_data = dec_resp.json()
    dec_id = dec_data["id"]
    assert len(dec_data["options"]) == 2

    analyze_resp = client.post(f"/api/decisions/{dec_id}/analyze")
    assert analyze_resp.status_code == 200
    analyze_data = analyze_resp.json()
    assert analyze_data["recommendation"] is not None
    assert analyze_data["confidence"] in ["HIGH", "MEDIUM", "LOW"]
    assert len(analyze_data["options_analysis"]) == 2

    # =========================================================================
    # 5. WHAT-IF SIMULATION (2 hours vs 4 hours)
    # =========================================================================
    baseline_resp = client.get(f"/api/scenarios/baseline?decision_id={dec_id}")
    assert baseline_resp.status_code == 200
    baseline_scenario = baseline_resp.json()
    baseline_id = baseline_scenario["id"]
    assert baseline_scenario["is_baseline"] is True

    # Scenario B: 2 hours/day (120 min)
    scen_resp = client.post("/api/scenarios", json={
        "decision_id": dec_id,
        "name": f"Tight Capacity Simulation {uid}",
        "description": "Simulating available daily engineering capacity drop to 2h/day",
        "is_baseline": False,
        "parameters": {
            "available_time_minutes": 120,
            "budget": 250.0,
            "constraints": ["Daily available time max 120 minutes"],
            "deadline_shifts": {},
            "priority_overrides": {},
            "task_duration_multiplier": 1.0
        }
    })
    assert scen_resp.status_code == 201
    scen_data = scen_resp.json()
    scen_id = scen_data["id"]

    sim_resp = client.post(
        f"/api/scenarios/{scen_id}/simulate",
        json={"baseline_scenario_id": baseline_id},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert "baseline" in sim_data
    assert "scenario" in sim_data
    assert "differences" in sim_data
    assert "reasons" in sim_data
    assert "evidence" in sim_data
    assert "confidence" in sim_data

    # =========================================================================
    # 6. EVIDENCE EXPLORER & CONFLICT DETECTION
    # =========================================================================
    # Insufficient evidence on unknown claim
    ev_insuf_resp = client.post("/api/evidence/explore", json={
        "claim": "Superconducting quantum processors are strictly mandatory for database clustering.",
        "collection_id": col_id,
        "top_k": 3,
        "relevance_threshold": 0.50
    })
    assert ev_insuf_resp.status_code == 200
    assert ev_insuf_resp.json()["has_sufficient_evidence"] is False
    assert ev_insuf_resp.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert ev_insuf_resp.json()["evidence_items"] == []

    # Upload conflicting note to test conflict detection
    conflict_text = (
        f"Server Infrastructure Alternate Policy {uid}:\n"
        "Approved infrastructure monthly budget is strictly capped at $800 due to growth.\n"
        "The previous $500 monthly budget limit is superseded and no longer valid.\n"
    )
    conflict_upload = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"conflict_policy_{uid}.txt", conflict_text.encode("utf-8"), "text/plain")},
    )
    assert conflict_upload.status_code == 201
    conflict_doc_id = conflict_upload.json()["id"]

    # Also upload a doc asserting $500
    budget_500_text = (
        f"Server Infrastructure Baseline Budget {uid}:\n"
        "Approved infrastructure monthly budget is strictly capped at $500.\n"
    )
    client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"budget_500_{uid}.txt", budget_500_text.encode("utf-8"), "text/plain")},
    )

    ev_conf_resp = client.post("/api/evidence/explore", json={
        "claim": "Approved infrastructure monthly budget is strictly capped at $500",
        "collection_id": col_id,
        "top_k": 6,
        "relevance_threshold": 0.20
    })
    assert ev_conf_resp.status_code == 200
    ev_conf_data = ev_conf_resp.json()
    assert ev_conf_data["has_sufficient_evidence"] is True
    assert ev_conf_data["conflict_detected"] is True
    assert ev_conf_data["status"] == "CONFLICT_DETECTED"

    # =========================================================================
    # 7. DASHBOARD TELEMETRY ENDPOINT
    # =========================================================================
    stats_resp = client.get("/api/dashboard/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["documents_count"] >= 2
    assert stats_data["goals_total"] >= 1
    assert stats_data["tasks_total"] >= 1
    assert stats_data["decisions_total"] >= 1
    assert stats_data["scenarios_total"] >= 1
    assert len(stats_data["recent_activities"]) > 0

    # =========================================================================
    # 8. HISTORY & AUDIT LOGGING ENDPOINTS
    # =========================================================================
    hist_resp = client.get("/api/history?limit=20")
    assert hist_resp.status_code == 200
    hist_logs = hist_resp.json()
    assert len(hist_logs) > 0

    hist_stats_resp = client.get("/api/history/stats")
    assert hist_stats_resp.status_code == 200
    assert hist_stats_resp.json()["total_events"] > 0

    # =========================================================================
    # 9. SETTINGS & CONFIGURATION ENDPOINTS
    # =========================================================================
    settings_resp = client.get("/api/settings")
    assert settings_resp.status_code == 200
    assert settings_resp.json()["llm_provider"] == "Gemini"
    assert settings_resp.json()["vector_store_type"] == "ChromaDB"

    update_settings_resp = client.put("/api/settings", json={
        "default_top_k": 8,
        "default_relevance_threshold": 0.35,
    })
    assert update_settings_resp.status_code == 200
    assert update_settings_resp.json()["default_top_k"] == 8
    assert update_settings_resp.json()["default_relevance_threshold"] == 0.35

    verify_engine_resp = client.post("/api/settings/verify-engine")
    assert verify_engine_resp.status_code == 200
    assert verify_engine_resp.json()["status"] == "ok"

    # =========================================================================
    # 10. DOCUMENT DELETION & VECTOR PURGE
    # =========================================================================
    del_doc_resp = client.delete(f"/api/documents/{conflict_doc_id}")
    assert del_doc_resp.status_code in [200, 204]

    # Verify document is gone
    get_doc_resp = client.get(f"/api/documents/{conflict_doc_id}")
    assert get_doc_resp.status_code == 404

    # =========================================================================
    # 11. PERSISTENCE ACROSS RESTART / NEW DB SESSION
    # =========================================================================
    db_session = SessionLocal()
    try:
        user_repo = UserRepository(db_session)
        user = user_repo.get_or_create_default()
        
        goal_repo = GoalRepository(db_session)
        persisted_goal = goal_repo.get(goal_id)
        assert persisted_goal is not None
        assert persisted_goal.title == f"Production Readiness {uid}"

        task_repo = TaskRepository(db_session)
        persisted_task = task_repo.get(task_id)
        assert persisted_task is not None
        assert persisted_task.title == f"Provision 16GB Cluster {uid}"

        dec_repo = DecisionRepository(db_session)
        persisted_dec = dec_repo.get(dec_id)
        assert persisted_dec is not None
        assert persisted_dec.title == f"Database Clustering Strategy {uid}"

        scen_repo = ScenarioRepository(db_session)
        persisted_scen = scen_repo.get(scen_id)
        assert persisted_scen is not None
        assert persisted_scen.name == f"Tight Capacity Simulation {uid}"
    finally:
        db_session.close()
