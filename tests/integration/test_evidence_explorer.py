import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.session import SessionLocal
from app.models.user import User
from app.models.collection import Collection
from app.models.evidence_analysis import EvidenceInvestigation, Evidence

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_evidence_explorer_full_pipeline(client, db_session):
    user = db_session.query(User).first()
    assert user is not None, "A default user must exist"

    # 1. Create a dedicated test collection
    unique_suffix = uuid.uuid4().hex[:6]
    col_name = f"Evidence Test Col {unique_suffix}"
    col_res = client.post("/api/collections", json={
        "name": col_name,
        "description": "Collection for testing Evidence Explorer and conflict detection"
    })
    assert col_res.status_code in (200, 201), col_res.text
    collection_id = col_res.json()["id"]

    # 2. Upload Document A (Capacity & Budget Policy)
    doc_a_content = (
        f"LifeOps Policy Document Alpha ({unique_suffix}):\n"
        "Standard operating capacity requires 4 hours daily focused allocation.\n"
        "Approved infrastructure monthly budget is strictly capped at $500.\n"
        "All microservice deployments must complete before Friday 5 PM.\n"
    )
    doc_a_res = client.post(
        "/api/documents/upload",
        data={"collection_id": collection_id},
        files={"file": (f"policy_alpha_{unique_suffix}.txt", doc_a_content.encode("utf-8"), "text/plain")}
    )
    assert doc_a_res.status_code in (200, 201), doc_a_res.text

    # 3. Test 1: Supported claim with real document evidence
    claim_1 = "Standard operating capacity requires 4 hours daily focused allocation"
    explore_res_1 = client.post("/api/evidence/explore", json={
        "claim": claim_1,
        "collection_id": collection_id,
        "top_k": 5,
        "relevance_threshold": 0.25,
    })
    assert explore_res_1.status_code == 200, explore_res_1.text
    data_1 = explore_res_1.json()

    assert data_1["has_sufficient_evidence"] is True
    assert data_1["status"] in ("VERIFIED_SUPPORT", "SUPPORTED")
    assert data_1["conflict_detected"] is False
    assert len(data_1["evidence_items"]) > 0
    assert len(data_1["conflicts"]) == 0

    first_item = data_1["evidence_items"][0]
    assert first_item["claim"] == claim_1
    assert f"policy_alpha_{unique_suffix}.txt" in first_item["source_filename"]
    assert first_item["page_number"] is not None
    assert first_item["relevance"] > 0.0
    assert len(first_item["reasoning"]) > 0
    assert first_item["confidence"] > 0.5
    assert first_item["uncertainty"] < 0.5
    assert first_item["stance"] == "SUPPORTS"
    assert "4 hours daily" in first_item["chunk_text"]

    # 4. Upload Document B (Conflicting Budget Directive)
    doc_b_content = (
        f"LifeOps Budget Addendum Beta ({unique_suffix}):\n"
        "Due to GPU scaling requirements, approved infrastructure monthly budget has been increased to $800.\n"
        "The previous $500 monthly budget limit is superseded and no longer valid.\n"
    )
    doc_b_res = client.post(
        "/api/documents/upload",
        data={"collection_id": collection_id},
        files={"file": (f"budget_beta_{unique_suffix}.txt", doc_b_content.encode("utf-8"), "text/plain")}
    )
    assert doc_b_res.status_code in (200, 201), doc_b_res.text

    # 5. Test 2: Conflict Detection when sources disagree
    claim_conflict = "Approved infrastructure monthly budget is strictly capped at $500"
    explore_conflict = client.post("/api/evidence/explore", json={
        "claim": claim_conflict,
        "collection_id": collection_id,
        "top_k": 6,
        "relevance_threshold": 0.20,
    })
    assert explore_conflict.status_code == 200, explore_conflict.text
    data_conflict = explore_conflict.json()

    assert data_conflict["has_sufficient_evidence"] is True
    assert data_conflict["conflict_detected"] is True
    assert data_conflict["status"] == "CONFLICT_DETECTED"
    assert len(data_conflict["conflicts"]) > 0

    conflict_item = data_conflict["conflicts"][0]
    assert "source_a" in conflict_item and "source_b" in conflict_item
    assert "discrepancy_explanation" in conflict_item
    assert conflict_item["severity"] in ("HIGH", "MEDIUM")

    # Verify both conflicting sources appear across evidence items
    filenames_found = {ev["source_filename"] for ev in data_conflict["evidence_items"]}
    assert f"policy_alpha_{unique_suffix}.txt" in filenames_found or f"budget_beta_{unique_suffix}.txt" in filenames_found

    # 6. Test 3: Insufficient Evidence — Never Fabricate Citations
    missing_claim = "The nuclear fusion reactor at facility omega requires quarterly maintenance"
    missing_res = client.post("/api/evidence/explore", json={
        "claim": missing_claim,
        "collection_id": collection_id,
        "top_k": 5,
        "relevance_threshold": 0.50,
    })
    assert missing_res.status_code == 200, missing_res.text
    data_missing = missing_res.json()

    assert data_missing["has_sufficient_evidence"] is False
    assert data_missing["status"] == "INSUFFICIENT_EVIDENCE"
    assert data_missing["evidence_items"] == []  # ZERO fabricated citations
    assert data_missing["conflicts"] == []
    assert data_missing["confidence"] == 0.0
    assert data_missing["uncertainty"] == 1.0

    # 7. Test 4: Relational Persistence and Retrieval
    list_res = client.get("/api/evidence")
    assert list_res.status_code == 200, list_res.text
    inv_list = list_res.json()
    assert len(inv_list) >= 3

    # Check conflicts endpoint
    conflicts_res = client.get("/api/evidence/conflicts")
    assert conflicts_res.status_code == 200, conflicts_res.text
    conf_list = conflicts_res.json()
    assert any(c["id"] == data_conflict["investigation_id"] for c in conf_list)

    # Check detail retrieval endpoint
    detail_res = client.get(f"/api/evidence/{data_conflict['investigation_id']}")
    assert detail_res.status_code == 200, detail_res.text
    detail_data = detail_res.json()
    assert detail_data["claim"] == claim_conflict
    assert detail_data["conflict_detected"] is True
    assert len(detail_data["conflicts"]) > 0

    # Verify DB persistence of individual Evidence items
    db_items = db_session.query(Evidence).filter(Evidence.investigation_id == data_conflict["investigation_id"]).all()
    assert len(db_items) > 0
    assert all(item.claim == claim_conflict for item in db_items)
