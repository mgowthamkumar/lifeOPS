import sys
from pathlib import Path

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.database.session import SessionLocal
from app.models.collection import Collection
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.services.document_service import document_service
from app.services.rag_service import rag_service
from app.services.llm_service import GeminiProvider, llm_service

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_rag_query_with_evidence(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    # 1. Create Collection
    col = Collection(
        user_id=user_id,
        name="RAG Career Collection",
        description="Testing question with evidence",
    )
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    # 2. Upload document with explicit factual evidence
    doc_content = (
        b"Candidate Resume:\n"
        b"Name: Sarah Jenkins\n"
        b"Expertise: 6 years of production experience in Python, FastAPI, and ChromaDB vector search.\n"
        b"Education: Master of Science in Artificial Intelligence from Stanford University.\n"
        b"Certifications: Certified Kubernetes Administrator and AWS Solutions Architect."
    )
    doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="sarah_resume.txt",
        content_bytes=doc_content,
        user_id=user_id,
    )
    assert doc.status == "PROCESSED"

    # 3. Query with question directly answered by evidence
    question = "What degree and expertise does Sarah Jenkins hold in Python and AI?"
    response = rag_service.query(
        db=db_session,
        collection_id=col.id,
        question=question,
        top_k=3,
        relevance_threshold=0.20,
        user_id=user_id,
    )

    # 4. Assert grounded answer with sufficient evidence and valid sources
    assert response.has_sufficient_evidence is True
    assert "INSUFFICIENT EVIDENCE" not in response.answer.upper()
    assert response.confidence_score > 0.5
    assert len(response.sources) > 0
    assert response.sources[0].document_name == "sarah_resume.txt"
    assert response.sources[0].similarity_score > 0.0

    # Cleanup
    document_service.delete_document(db_session, doc.id)
    db_session.delete(col)
    db_session.commit()

def test_rag_query_without_evidence_returns_insufficient_evidence(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    # 1. Create Collection
    col = Collection(
        user_id=user_id,
        name="RAG Hardware Specs",
        description="Testing question without evidence",
    )
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    # 2. Upload document about unrelated domain (server hardware)
    doc_content = (
        b"Server Infrastructure Manual:\n"
        b"Node A: Dell PowerEdge R750 with dual Intel Xeon Silver 4314 CPUs.\n"
        b"RAM: 256GB ECC DDR4 memory.\n"
        b"Storage: 4x 3.84TB NVMe SSD in RAID 10 configuration."
    )
    doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="server_hardware.txt",
        content_bytes=doc_content,
        user_id=user_id,
    )
    assert doc.status == "PROCESSED"

    # 3. Ask completely ungrounded question with zero evidence in the document
    question = "What is the recommended dosage of medication for cardiac arrhythmia?"
    response = rag_service.query(
        db=db_session,
        collection_id=col.id,
        question=question,
        top_k=3,
        relevance_threshold=0.35,
        user_id=user_id,
    )

    # 4. Strictly verify that INSUFFICIENT EVIDENCE is produced and NO sources are hallucinated
    assert response.has_sufficient_evidence is False
    assert "INSUFFICIENT EVIDENCE" in response.answer.upper()
    assert response.confidence_score == 0.0
    assert len(response.sources) == 0, "No hallucinated source is allowed when evidence is insufficient."

    # Cleanup
    document_service.delete_document(db_session, doc.id)
    db_session.delete(col)
    db_session.commit()

def test_rag_query_empty_collection(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    col = Collection(
        user_id=user_id,
        name="Empty Knowledge Base",
        description="Testing empty collection handling",
    )
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    response = rag_service.query(
        db=db_session,
        collection_id=col.id,
        question="How do I configure the load balancer?",
        user_id=user_id,
    )

    assert response.has_sufficient_evidence is False
    assert "INSUFFICIENT EVIDENCE" in response.answer.upper()
    assert len(response.sources) == 0
    assert response.confidence_score == 0.0

    # Cleanup
    db_session.delete(col)
    db_session.commit()
