import sys
from pathlib import Path

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_full_rag_api_pipeline(client: TestClient):
    # 1. Create a Collection for RAG
    col_resp = client.post(
        "/api/collections",
        json={"name": "Financial Policy KB", "description": "Budget and expenditure guidelines"},
    )
    assert col_resp.status_code == 201
    col_id = col_resp.json()["id"]

    # 2. Upload real document with concrete policy figures
    content = (
        b"LifeOps Corporation Financial Policy 2026:\n"
        b"1. The Q1 marketing expansion budget is allocated at $75,000.\n"
        b"2. The Q2 engineering recruiting and team budget is strictly capped at $150,000.\n"
        b"3. Emergency contingency reserve fund is held at $25,000.\n"
        b"4. Discretionary expenses above $2,500 require dual executive approval."
    )
    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("financial_policy_2026.txt", content, "text/plain")},
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["status"] == "PROCESSED"

    # 3. Test question WITH direct evidence
    query_payload = {
        "collection_id": col_id,
        "question": "What is the Q2 engineering recruiting budget and contingency fund?",
        "top_k": 3,
        "relevance_threshold": 0.20,
    }
    ans_resp = client.post("/api/rag/query", json=query_payload)
    assert ans_resp.status_code == 200
    res_data = ans_resp.json()

    assert res_data["has_sufficient_evidence"] is True
    assert "INSUFFICIENT EVIDENCE" not in res_data["answer"].upper()
    assert len(res_data["sources"]) > 0
    assert res_data["sources"][0]["document_name"] == "financial_policy_2026.txt"
    assert res_data["confidence_score"] > 0.5

    # 4. Test question WITHOUT evidence
    no_evidence_payload = {
        "collection_id": col_id,
        "question": "What is the flight schedule from Tokyo to Honolulu tomorrow morning?",
        "top_k": 3,
        "relevance_threshold": 0.35,
    }
    no_ev_resp = client.post("/api/rag/query", json=no_evidence_payload)
    assert no_ev_resp.status_code == 200
    no_ev_data = no_ev_resp.json()

    # Must produce INSUFFICIENT EVIDENCE and NO hallucinated sources
    assert no_ev_data["has_sufficient_evidence"] is False
    assert "INSUFFICIENT EVIDENCE" in no_ev_data["answer"].upper()
    assert len(no_ev_data["sources"]) == 0
    assert no_ev_data["confidence_score"] == 0.0

    # 5. Check evidence history endpoint
    ev_resp = client.get("/api/rag/evidence")
    assert ev_resp.status_code == 200
    evidence_list = ev_resp.json()
    assert len(evidence_list) > 0
    assert any(e["source_filename"] == "financial_policy_2026.txt" for e in evidence_list)

    # 6. Cleanup collection
    cleanup_resp = client.delete(f"/api/collections/{col_id}")
    assert cleanup_resp.status_code == 204
