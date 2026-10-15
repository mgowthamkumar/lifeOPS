import io
import sys
from pathlib import Path
import tempfile
import os

# Add backend directory to sys.path
backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.main import app
from app.services.vector_store import vector_store_service

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def create_sample_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Add text to second page using metadata or page annotation
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def create_sample_docx() -> bytes:
    doc = DocxDocument()
    doc.add_heading("AI Engineering Requirements", 0)
    doc.add_paragraph("Candidates must have experience with Python, FastAPI, and vector databases.")
    doc.add_paragraph("Prior experience with ChromaDB and retrieval systems is preferred.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Skill"
    table.rows[0].cells[1].text = "Level"
    table.rows[1].cells[0].text = "Python"
    table.rows[1].cells[1].text = "Advanced"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_full_document_pipeline(client: TestClient):
    # 1. Create a collection
    col_resp = client.post(
        "/api/collections",
        json={"name": "Career Pipeline Test", "description": "Testing multi-format ingestion"},
    )
    assert col_resp.status_code == 201
    col_data = col_resp.json()
    col_id = col_data["id"]

    # 2. Upload TXT Document
    txt_content = b"Candidate Profile: 3 years experience with Python, Machine Learning, and PyTorch. Looking for AI internships."
    txt_upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("candidate_profile.txt", txt_content, "text/plain")},
    )
    assert txt_upload_resp.status_code == 201
    txt_doc = txt_upload_resp.json()
    assert txt_doc["status"] == "PROCESSED"
    assert txt_doc["chunk_count"] > 0
    txt_doc_id = txt_doc["id"]

    # 3. Upload Markdown Document
    md_content = b"# Internship Notice\n\nDeadline: Next Friday.\nRequirements: FastAPI backend, Python, and ChromaDB vector search."
    md_upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("internship_notice.md", md_content, "text/markdown")},
    )
    assert md_upload_resp.status_code == 201
    md_doc = md_upload_resp.json()
    assert md_doc["status"] == "PROCESSED"
    md_doc_id = md_doc["id"]

    # 4. Upload CSV Document
    csv_content = b"Role,Experience,KeySkill,Deadline\nAI Engineer,Intermediate,Python and RAG,2026-11-01\nData Scientist,Beginner,SQL and Stats,2026-12-01"
    csv_upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("roles_summary.csv", csv_content, "text/csv")},
    )
    assert csv_upload_resp.status_code == 201
    csv_doc = csv_upload_resp.json()
    assert csv_doc["status"] == "PROCESSED"

    # 5. Upload DOCX Document
    docx_bytes = create_sample_docx()
    docx_upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("ai_requirements.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert docx_upload_resp.status_code == 201
    docx_doc = docx_upload_resp.json()
    assert docx_doc["status"] == "PROCESSED"

    # 6. Verify vectors exist in persistent ChromaDB
    total_vectors = vector_store_service.count(col_id)
    assert total_vectors >= 4, f"Expected at least 4 vectors in ChromaDB, found {total_vectors}"

    # Verify semantic query on ChromaDB
    query_result = vector_store_service.query_vectors(
        collection_name=col_id,
        query_embeddings=[[0.1] * 384],
        n_results=2,
    )
    assert len(query_result["ids"][0]) == 2

    # 7. Test Reprocess Document
    reprocess_resp = client.post(f"/api/documents/{txt_doc_id}/reprocess")
    assert reprocess_resp.status_code == 200
    assert reprocess_resp.json()["status"] == "PROCESSED"

    # 8. Test Update Document (New Version)
    updated_txt_content = b"Candidate Profile v2: Added 1 year of production FastAPI, Docker, and agentic workflows experience."
    update_resp = client.put(
        f"/api/documents/{txt_doc_id}/update",
        files={"file": ("candidate_profile_v2.txt", updated_txt_content, "text/plain")},
    )
    assert update_resp.status_code == 200
    updated_doc = update_resp.json()
    assert updated_doc["current_version"] == 2
    assert updated_doc["status"] == "PROCESSED"

    # Verify old vectors were replaced and total vector count remains accurate
    vectors_after_update = vector_store_service.count(col_id)
    assert vectors_after_update >= 4

    # 9. Test Delete Document and Verify Vector Removal
    del_resp = client.delete(f"/api/documents/{md_doc_id}")
    assert del_resp.status_code == 204

    # Confirm vectors for md_doc_id were removed from ChromaDB
    remaining_vectors = vector_store_service.count(col_id)
    assert remaining_vectors < vectors_after_update

    # 10. Clean up collection
    cleanup_resp = client.delete(f"/api/collections/{col_id}")
    assert cleanup_resp.status_code == 204

def test_reprocess_document_recovers_missing_active_version(client: TestClient):
    from app.database.session import SessionLocal
    from app.models.document import DocumentVersion, DocumentChunk

    # 1. Create a collection and document
    col_resp = client.post(
        "/api/collections",
        json={"name": "Version Recovery Test", "description": "Testing missing active version fallback"},
    )
    col_id = col_resp.json()["id"]

    upload_resp = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("test_recovery.txt", b"Version fallback test content", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    # 2. Simulate absent active version by marking all versions as inactive
    with SessionLocal() as db:
        versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).all()
        for v in versions:
            v.is_active = False
        db.commit()

    # 3. Call reprocess endpoint
    reprocess_resp = client.post(f"/api/documents/{doc_id}/reprocess")
    assert reprocess_resp.status_code == 200

    # 4. Verify all chunks have a valid version_id pointing to DocumentVersion and not doc.id
    with SessionLocal() as db:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        assert len(chunks) > 0
        valid_version_ids = {v.id for v in db.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).all()}
        for chunk in chunks:
            assert chunk.version_id in valid_version_ids
            assert chunk.version_id != doc_id

    # Cleanup
    client.delete(f"/api/collections/{col_id}")
