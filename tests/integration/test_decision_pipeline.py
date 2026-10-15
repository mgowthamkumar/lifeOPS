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
from app.repositories.decision_repository import DecisionRepository
from app.models.decision import Decision

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_decision_intelligence_full_pipeline(client: TestClient):
    uid = uuid.uuid4().hex[:6]

    # 1. Create a Strategic Goal
    goal_resp = client.post("/api/goals", json={
        "title": f"Scale Backend Infrastructure {uid}",
        "description": "Achieve high throughput and sub-50ms response times",
        "importance": "CRITICAL",
        "status": "ACTIVE",
        "progress": 30.0,
    })
    assert goal_resp.status_code == 201
    goal = goal_resp.json()
    goal_id = goal["id"]

    # 2. Create Collection and Upload Real Document with System Evidence
    col_resp = client.post("/api/collections", json={
        "name": f"Architecture Benchmarks {uid}",
        "description": "System architecture performance benchmarks and guidelines",
    })
    assert col_resp.status_code == 201
    col_id = col_resp.json()["id"]

    doc_text = (
        "Architecture Benchmark Report 2026: "
        "A distributed Redis cluster delivers consistent p99 read latency under 15ms with low maintenance overhead. "
        "Serverless Edge Functions experience cold-start latency spikes exceeding 350ms and incur unpredictable monthly costs under high concurrency."
    )
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": (f"benchmark_report_{uid}.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc = upload_resp.json()
    assert doc["status"] == "PROCESSED"

    # 3. User Creates Decision with Question, Context, Goals, Constraints, and Options
    decision_payload = {
        "title": f"Caching Tier Architecture Decision {uid}",
        "question": "Which caching tier should we deploy to handle high concurrency while keeping p99 latency under 50ms?",
        "context_description": "We are preparing for 100k user scale and need reliable low-latency caching before launch.",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        "constraints": [
            "Monthly operational budget under $600",
            "P99 query latency under 50ms",
            "Zero downtime automated failover",
        ],
        "goal_ids": [goal_id],
        "options": [
            {
                "title": "Distributed Redis Cluster",
                "description": "Deploy managed in-memory Redis cluster with automated replication and sentinel failover.",
                "effort_estimate": "MEDIUM",
            },
            {
                "title": "Serverless Edge Functions Cache",
                "description": "Implement distributed key-value edge compute functions across external edge network.",
                "effort_estimate": "HIGH",
            },
        ],
    }

    create_resp = client.post("/api/decisions", json=decision_payload)
    assert create_resp.status_code == 201
    decision_data = create_resp.json()
    decision_id = decision_data["id"]

    assert decision_data["title"] == decision_payload["title"]
    assert decision_data["question"] == decision_payload["question"]
    assert decision_data["status"] == "DRAFT"
    assert len(decision_data["goals"]) == 1
    assert decision_data["goals"][0]["id"] == goal_id
    assert len(decision_data["options"]) == 2
    assert len(decision_data["constraints"]) == 3

    redis_opt_id = next(o["id"] for o in decision_data["options"] if "Redis" in o["title"])
    edge_opt_id = next(o["id"] for o in decision_data["options"] if "Edge" in o["title"])

    # 4. Execute Decision Intelligence Analysis
    analyze_resp = client.post(f"/api/decisions/{decision_id}/analyze")
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()

    # Validate analysis fields returned per specifications:
    assert analysis["decision_id"] == decision_id
    assert analysis["recommendation"]
    assert analysis["confidence"] in ["HIGH", "MEDIUM", "LOW"]
    assert analysis["reasoning_summary"]
    assert analysis["top_option_id"] == redis_opt_id
    assert len(analysis["options_analysis"]) == 2

    # Verify all required option fields: match, strengths, weaknesses, gaps, constraints, goal alignment, evidence, confidence, recommendation
    redis_analysis = next(o for o in analysis["options_analysis"] if o["option_id"] == redis_opt_id)
    edge_analysis = next(o for o in analysis["options_analysis"] if o["option_id"] == edge_opt_id)

    for opt_item in [redis_analysis, edge_analysis]:
        assert "match" in opt_item
        assert isinstance(opt_item["match"], (int, float))
        assert 0.0 <= opt_item["match"] <= 100.0

        assert "strengths" in opt_item
        assert isinstance(opt_item["strengths"], list)
        assert len(opt_item["strengths"]) > 0

        assert "weaknesses" in opt_item
        assert isinstance(opt_item["weaknesses"], list)
        assert len(opt_item["weaknesses"]) > 0

        assert "gaps" in opt_item
        assert isinstance(opt_item["gaps"], list)
        assert len(opt_item["gaps"]) > 0

        assert "constraints" in opt_item
        assert isinstance(opt_item["constraints"], list)
        assert len(opt_item["constraints"]) > 0

        assert "goal_alignment" in opt_item
        assert isinstance(opt_item["goal_alignment"], str)
        assert len(opt_item["goal_alignment"]) > 0

        assert "evidence" in opt_item
        assert isinstance(opt_item["evidence"], list)

        assert "confidence" in opt_item
        assert isinstance(opt_item["confidence"], (int, float))
        assert 0.0 <= opt_item["confidence"] <= 1.0

        assert "recommendation" in opt_item
        assert opt_item["recommendation"] in ["STRONGLY RECOMMENDED", "VIABLE ALTERNATIVE", "NOT RECOMMENDED"]

    # Redis has grounded evidence in the document and lower effort, so its match score must exceed Edge
    assert redis_analysis["match"] > edge_analysis["match"]
    assert len(redis_analysis["evidence"]) > 0
    assert "Redis" in redis_analysis["evidence"][0]

    # 5. Verify Persistence via API
    get_resp = client.get(f"/api/decisions/{decision_id}")
    assert get_resp.status_code == 200
    retrieved_decision = get_resp.json()
    assert retrieved_decision["status"] == "ANALYZED"
    assert retrieved_decision["latest_analysis"] is not None
    assert retrieved_decision["latest_analysis"]["top_option_id"] == redis_opt_id
    assert len(retrieved_decision["latest_analysis"]["options_analysis"]) == 2

    for opt in retrieved_decision["options"]:
        assert opt["match_score"] is not None
        assert opt["match_score"] > 0

    # 6. Verify Persistence across Fresh Database Session
    with SessionLocal() as db_session:
        db_repo = DecisionRepository(db_session)
        db_decision = db_repo.get_with_relations(decision_id)
        assert db_decision is not None
        assert db_decision.status == "ANALYZED"
        assert len(db_decision.options) == 2
        assert len(db_decision.analysis_results) >= 1
        assert db_decision.latest_analysis is not None
        assert db_decision.latest_analysis["top_option_id"] == redis_opt_id

    # 7. Select Option to Mark Decision as DECIDED
    select_resp = client.patch(
        f"/api/decisions/{decision_id}/select-option",
        json={"option_id": redis_opt_id},
    )
    assert select_resp.status_code == 200
    decided_data = select_resp.json()
    assert decided_data["status"] == "DECIDED"
    assert decided_data["selected_option_id"] == redis_opt_id

    # Final DB check
    with SessionLocal() as db_session:
        db_repo = DecisionRepository(db_session)
        final_decision = db_repo.get(decision_id)
        assert final_decision.status == "DECIDED"
        assert final_decision.selected_option_id == redis_opt_id
