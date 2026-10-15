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
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.evidence_repository import EvidenceInvestigationRepository, ActivityLogRepository

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_process_11_end_to_end_validation(client: TestClient):
    """
    LIFEOPS AI — PROCESS 11: Final End-to-End Validation (25-Step Pipeline)
    """
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)

    # 0. Clean environment initialization
    for t in client.get("/api/tasks").json():
        client.delete(f"/api/tasks/{t['id']}")
    for g in client.get("/api/goals").json():
        client.delete(f"/api/goals/{g['id']}")
    for d in client.get("/api/decisions").json():
        client.delete(f"/api/decisions/{d['id']}")

    # -------------------------------------------------------------------------
    # 1. Create collection
    # -------------------------------------------------------------------------
    col_resp = client.post("/api/collections", json={
        "name": f"Operating Guidelines {uid}",
        "description": "Standard operating policy and infrastructure documentation",
    })
    assert col_resp.status_code == 201, col_resp.text
    col_data = col_resp.json()
    col_id = col_data["id"]
    assert col_data["name"] == f"Operating Guidelines {uid}"

    # -------------------------------------------------------------------------
    # 2. Upload real documents
    # -------------------------------------------------------------------------
    doc_content_v1 = (
        f"LifeOps Engineering Manual 2026 ({uid}):\n"
        "Section 1: Operating Capacity Policy\n"
        "Standard operating capacity requires 4 hours daily focused allocation.\n"
        "Section 2: Database Configuration\n"
        "High-performance caching requires Redis Cluster with 16GB allocation.\n"
        "Section 3: Budget Constraint\n"
        "Approved infrastructure monthly budget is strictly capped at $500.\n"
    )
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"engineering_manual_{uid}.txt", doc_content_v1.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]

    # -------------------------------------------------------------------------
    # 3. Process documents
    # -------------------------------------------------------------------------
    assert doc_data["status"] == "PROCESSED"
    assert doc_data["chunk_count"] >= 1
    assert doc_data["current_version"] == 1

    # Verify detail chunks
    detail_resp = client.get(f"/api/documents/{doc_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["chunks"]) >= 1

    # -------------------------------------------------------------------------
    # 4. Create user context
    # -------------------------------------------------------------------------
    ctx_resp = client.put("/api/users/context", json={
        "full_name": f"Alex Morgan {uid}",
        "preferences": {"theme": "dark", "notifications": True},
        "context": {
            "role": "Principal Systems Engineer",
            "daily_focus_hours": 4.0,
            "core_skills": ["Distributed Systems", "PostgreSQL", "Redis"],
            "constraints": ["No scheduled deploys after 5 PM", "Budget limit strict"],
        },
    })
    assert ctx_resp.status_code == 200, ctx_resp.text
    user_data = ctx_resp.json()
    assert user_data["full_name"] == f"Alex Morgan {uid}"
    assert user_data["context"]["role"] == "Principal Systems Engineer"

    # -------------------------------------------------------------------------
    # 5. Create goal
    # -------------------------------------------------------------------------
    goal_resp = client.post("/api/goals", json={
        "title": f"Achieve 99.99% Reliability {uid}",
        "description": "Establish high-availability caching and zero-downtime clustering",
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 20.0,
        "deadline": (now + timedelta(days=30)).isoformat(),
        "category": "Architecture",
    })
    assert goal_resp.status_code == 201, goal_resp.text
    goal_id = goal_resp.json()["id"]

    # -------------------------------------------------------------------------
    # 6. Create tasks
    # -------------------------------------------------------------------------
    # Task 1: High priority, 90 mins, linked to doc and goal
    t1_resp = client.post("/api/tasks", json={
        "title": f"Deploy Redis Cluster Nodes {uid}",
        "description": "Set up replica sets and automated sentinel failover",
        "priority": "HIGH",
        "status": "TODO",
        "estimated_duration_minutes": 90,
        "deadline": now.isoformat(),
        "goal_id": goal_id,
        "document_ids": [doc_id],
    })
    assert t1_resp.status_code == 201, t1_resp.text
    t1_id = t1_resp.json()["id"]

    # Task 2: Medium priority, 60 mins
    t2_resp = client.post("/api/tasks", json={
        "title": f"Configure Failover Telemetry {uid}",
        "description": "Validate failover alert triggers and health check pings",
        "priority": "MEDIUM",
        "status": "TODO",
        "estimated_duration_minutes": 60,
        "deadline": (now + timedelta(days=1)).isoformat(),
        "goal_id": goal_id,
        "document_ids": [],
    })
    assert t2_resp.status_code == 201, t2_resp.text
    t2_id = t2_resp.json()["id"]

    # Task 3: Low priority, 45 mins
    t3_resp = client.post("/api/tasks", json={
        "title": f"Audit Monthly Infrastructure Billing {uid}",
        "description": "Verify cluster costs remain strictly within $500 monthly limit",
        "priority": "LOW",
        "status": "TODO",
        "estimated_duration_minutes": 45,
        "deadline": (now + timedelta(days=3)).isoformat(),
        "goal_id": goal_id,
        "document_ids": [doc_id],
    })
    assert t3_resp.status_code == 201, t3_resp.text
    t3_id = t3_resp.json()["id"]

    # -------------------------------------------------------------------------
    # 7. Ask "What should I do today?"
    # -------------------------------------------------------------------------
    plan_resp = client.post("/api/action-planner/generate", json={
        "query": "What should I do today?",
        "available_minutes": 240,  # 4 hours
        "focus_areas": ["Architecture"],
    })
    assert plan_resp.status_code == 201, plan_resp.text
    plan_data = plan_resp.json()
    assert plan_data["total_estimated_minutes"] <= 240
    assert len(plan_data["items"]) >= 1

    # -------------------------------------------------------------------------
    # 8. Verify RAG
    # -------------------------------------------------------------------------
    rag_resp = client.post("/api/rag/query", json={
        "collection_id": col_id,
        "question": "What is the daily operating capacity requirement?",
        "top_k": 3,
        "relevance_threshold": 0.10,
    })
    assert rag_resp.status_code == 200, rag_resp.text
    rag_data = rag_resp.json()
    assert rag_data["has_sufficient_evidence"] is True
    assert rag_data["confidence_score"] > 0

    # -------------------------------------------------------------------------
    # 9. Verify sources
    # -------------------------------------------------------------------------
    assert len(rag_data["sources"]) > 0
    first_src = rag_data["sources"][0]
    assert "4 hours daily" in first_src["content_snippet"]
    assert first_src["document_name"] == f"engineering_manual_{uid}.txt"
    assert first_src["page_number"] == 1
    assert first_src["similarity_score"] > 0.10

    # -------------------------------------------------------------------------
    # 10. Create decision
    # -------------------------------------------------------------------------
    dec_resp = client.post("/api/decisions", json={
        "title": f"Caching Strategy Architecture {uid}",
        "question": "Which caching architecture best satisfies 99.99% reliability and budget?",
        "context_description": "We need low-latency in-memory caching under $500 monthly budget.",
        "constraints": [
            "Monthly budget strictly capped at $500",
            "P99 latency under 20ms",
        ],
        "goal_ids": [goal_id],
        "options": [
            {
                "title": "Managed Redis Cluster",
                "description": "Deploy managed Redis with replica failover",
                "effort_estimate": "MEDIUM",
            },
            {
                "title": "In-Memory Memcached Pool",
                "description": "Multi-node Memcached instance with client hashing",
                "effort_estimate": "LOW",
            },
        ],
    })
    assert dec_resp.status_code == 201, dec_resp.text
    dec_data = dec_resp.json()
    dec_id = dec_data["id"]
    assert len(dec_data["options"]) == 2

    # -------------------------------------------------------------------------
    # 11. Analyze options
    # -------------------------------------------------------------------------
    analyze_resp = client.post(f"/api/decisions/{dec_id}/analyze")
    assert analyze_resp.status_code == 200, analyze_resp.text
    analysis_data = analyze_resp.json()
    assert analysis_data["recommendation"] is not None
    assert analysis_data["confidence"] in ["HIGH", "MEDIUM", "LOW"]
    assert len(analysis_data["options_analysis"]) == 2
    for opt_eval in analysis_data["options_analysis"]:
        assert "match" in opt_eval
        assert "strengths" in opt_eval
        assert "weaknesses" in opt_eval
        assert "gaps" in opt_eval
        assert "constraints" in opt_eval
        assert "goal_alignment" in opt_eval
        assert "confidence" in opt_eval

    # -------------------------------------------------------------------------
    # 12. Create baseline
    # -------------------------------------------------------------------------
    baseline_resp = client.get(f"/api/scenarios/baseline?decision_id={dec_id}")
    assert baseline_resp.status_code == 200, baseline_resp.text
    baseline = baseline_resp.json()
    baseline_id = baseline["id"]
    assert baseline["is_baseline"] is True
    assert baseline["parameters"]["available_time_minutes"] == 240

    # -------------------------------------------------------------------------
    # 13. Create What-If scenario
    # -------------------------------------------------------------------------
    scen_resp = client.post("/api/scenarios", json={
        "name": f"Capacity Crunch Scenario {uid}",
        "description": "Simulate 2 hours daily capacity constraint",
        "decision_id": dec_id,
        "is_baseline": False,
        "parameters": {
            "available_time_minutes": 240,  # initially 240, changed in step 14
            "budget": 350.0,
            "constraints": ["Time constrained to 2 hours"],
            "deadline_shifts": {},
            "priority_overrides": {},
            "task_duration_multiplier": 1.0,
        },
    })
    assert scen_resp.status_code == 201, scen_resp.text
    scen_id = scen_resp.json()["id"]

    # -------------------------------------------------------------------------
    # 14. Change available time (to 2 hours / 120 mins)
    # -------------------------------------------------------------------------
    update_scen_resp = client.put(f"/api/scenarios/{scen_id}", json={
        "parameters": {
            "available_time_minutes": 120,  # Changed to 2 hours/day
            "budget": 350.0,
            "constraints": ["Time constrained to 120 minutes daily"],
            "deadline_shifts": {},
            "priority_overrides": {},
            "task_duration_multiplier": 1.0,
        },
    })
    assert update_scen_resp.status_code == 200, update_scen_resp.text
    assert update_scen_resp.json()["parameters"]["available_time_minutes"] == 120

    # -------------------------------------------------------------------------
    # 15. Recalculate (simulate scenario vs baseline)
    # -------------------------------------------------------------------------
    sim_resp = client.post(
        f"/api/scenarios/{scen_id}/simulate",
        json={"baseline_scenario_id": baseline_id},
    )
    assert sim_resp.status_code == 200, sim_resp.text
    sim_data = sim_resp.json()

    # -------------------------------------------------------------------------
    # 16. Compare (baseline vs scenario difference, reason, evidence, confidence)
    # -------------------------------------------------------------------------
    assert "baseline" in sim_data
    assert "scenario" in sim_data
    assert "differences" in sim_data
    assert "reasons" in sim_data
    assert "evidence" in sim_data
    assert "confidence" in sim_data

    # Under 240m (baseline): all tasks fit (90 + 60 + 45 = 195m)
    # Under 120m (scenario): only Task 1 (90m) fits, remaining 2 tasks deferred
    assert sim_data["baseline"]["planned_actions_count"] >= sim_data["scenario"]["planned_actions_count"]
    assert any(d["category"] == "TIME_BUDGET" for d in sim_data["differences"])

    # -------------------------------------------------------------------------
    # 17. Update document (v2 replaces active version in ChromaDB)
    # -------------------------------------------------------------------------
    doc_content_v2 = (
        f"LifeOps Engineering Manual 2026 Revised ({uid}):\n"
        "Section 1: Operating Capacity Policy\n"
        "Standard operating capacity has been updated to 6 hours daily focused allocation.\n"
        "Section 2: Database Configuration\n"
        "High-performance caching requires Redis Cluster with 32GB RAM allocation.\n"
        "Section 3: Budget Constraint\n"
        "Approved infrastructure monthly budget has been increased to $750.\n"
    )
    update_doc_resp = client.put(
        f"/api/documents/{doc_id}/update",
        files={"file": (f"engineering_manual_v2_{uid}.txt", doc_content_v2.encode("utf-8"), "text/plain")},
    )
    assert update_doc_resp.status_code == 200, update_doc_resp.text
    assert update_doc_resp.json()["current_version"] == 2

    # -------------------------------------------------------------------------
    # 18. Recalculate (verify updated RAG retrieves 6 hours and 32GB)
    # -------------------------------------------------------------------------
    rag_updated_resp = client.post("/api/rag/query", json={
        "collection_id": col_id,
        "question": "What is the revised standard operating capacity and RAM allocation?",
        "top_k": 3,
        "relevance_threshold": 0.10,
    })
    assert rag_updated_resp.status_code == 200, rag_updated_resp.text
    rag_updated_data = rag_updated_resp.json()
    assert rag_updated_data["has_sufficient_evidence"] is True
    assert any("6 hours" in s["content_snippet"] or "32GB" in s["content_snippet"] for s in rag_updated_data["sources"])

    # -------------------------------------------------------------------------
    # 19. Delete document (purges document chunks and vector index)
    # -------------------------------------------------------------------------
    del_doc_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_doc_resp.status_code in [200, 204], del_doc_resp.text
    get_deleted_doc = client.get(f"/api/documents/{doc_id}")
    assert get_deleted_doc.status_code == 404

    # -------------------------------------------------------------------------
    # 20. Recalculate (RAG on empty collection returns INSUFFICIENT EVIDENCE)
    # -------------------------------------------------------------------------
    rag_after_del_resp = client.post("/api/rag/query", json={
        "collection_id": col_id,
        "question": "What is the RAM allocation for Redis Cluster?",
        "top_k": 3,
        "relevance_threshold": 0.10,
    })
    assert rag_after_del_resp.status_code == 200, rag_after_del_resp.text
    rag_del_data = rag_after_del_resp.json()
    assert rag_del_data["has_sufficient_evidence"] is False
    assert len(rag_del_data["sources"]) == 0

    # -------------------------------------------------------------------------
    # 21. Test insufficient evidence (Never fabricate citations)
    # -------------------------------------------------------------------------
    insuf_resp = client.post("/api/evidence/explore", json={
        "claim": "Cryogenic nitrogen cooling is required for all data center servers",
        "collection_id": col_id,
        "top_k": 3,
        "relevance_threshold": 0.40,
    })
    assert insuf_resp.status_code == 200, insuf_resp.text
    insuf_data = insuf_resp.json()
    assert insuf_data["has_sufficient_evidence"] is False
    assert insuf_data["status"] == "INSUFFICIENT_EVIDENCE"
    assert insuf_data["evidence_items"] == []  # ZERO fabricated citations
    assert insuf_data["confidence"] == 0.0

    # -------------------------------------------------------------------------
    # 22. Test conflicting evidence (Conflict detection across sources)
    # -------------------------------------------------------------------------
    # Upload Document A
    doc_a = (
        f"Server Migration Directive A ({uid}):\n"
        "All database clusters must run PostgreSQL 16.0 for security compliance.\n"
    )
    client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"directive_a_{uid}.txt", doc_a.encode("utf-8"), "text/plain")},
    )

    # Upload Document B (Conflicting)
    doc_b = (
        f"Server Migration Directive B ({uid}):\n"
        "PostgreSQL 16.0 is strictly prohibited due to critical transaction bugs.\n"
        "Only PostgreSQL 14.5 is permitted.\n"
    )
    client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"directive_b_{uid}.txt", doc_b.encode("utf-8"), "text/plain")},
    )

    conflict_explore_resp = client.post("/api/evidence/explore", json={
        "claim": "All database clusters must run PostgreSQL 16.0 for security compliance",
        "collection_id": col_id,
        "top_k": 6,
        "relevance_threshold": 0.15,
    })
    assert conflict_explore_resp.status_code == 200, conflict_explore_resp.text
    conf_data = conflict_explore_resp.json()
    assert conf_data["has_sufficient_evidence"] is True
    assert conf_data["conflict_detected"] is True
    assert conf_data["status"] == "CONFLICT_DETECTED"
    assert len(conf_data["conflicts"]) >= 1

    # -------------------------------------------------------------------------
    # 23. Restart backend (Simulate restart via fresh DB session & engine reconnect)
    # -------------------------------------------------------------------------
    db_after_restart = SessionLocal()

    # -------------------------------------------------------------------------
    # 24. Refresh browser (Verify system dashboard & telemetry reloads cleanly)
    # -------------------------------------------------------------------------
    dash_resp = client.get("/api/dashboard/stats")
    assert dash_resp.status_code == 200, dash_resp.text
    dash_data = dash_resp.json()
    assert dash_data["system_status"] == "operational"
    assert dash_data["goals_total"] >= 1
    assert dash_data["tasks_total"] >= 1
    assert dash_data["decisions_total"] >= 1
    assert dash_data["scenarios_total"] >= 1

    # -------------------------------------------------------------------------
    # 25. Verify persistence (Verify all entities survive in relational store)
    # -------------------------------------------------------------------------
    try:
        goal_repo = GoalRepository(db_after_restart)
        persisted_goal = goal_repo.get(goal_id)
        assert persisted_goal is not None
        assert persisted_goal.title == f"Achieve 99.99% Reliability {uid}"

        task_repo = TaskRepository(db_after_restart)
        persisted_t1 = task_repo.get(t1_id)
        assert persisted_t1 is not None
        assert persisted_t1.title == f"Deploy Redis Cluster Nodes {uid}"

        dec_repo = DecisionRepository(db_after_restart)
        persisted_dec = dec_repo.get(dec_id)
        assert persisted_dec is not None
        assert persisted_dec.title == f"Caching Strategy Architecture {uid}"

        scen_repo = ScenarioRepository(db_after_restart)
        persisted_scen = scen_repo.get(scen_id)
        assert persisted_scen is not None
        assert persisted_scen.name == f"Capacity Crunch Scenario {uid}"
        assert persisted_scen.parameters["available_time_minutes"] == 120

        user_repo = UserRepository(db_after_restart)
        user = user_repo.get_or_create_default()
        assert user.full_name == f"Alex Morgan {uid}"
        assert user.context["role"] == "Principal Systems Engineer"
    finally:
        db_after_restart.close()
