import sys
from pathlib import Path
from unittest.mock import patch

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.database.session import SessionLocal
from app.models.collection import Collection
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.repositories.user_repository import UserRepository
from app.services.document_service import document_service
from app.services.vector_store import vector_store_service

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_reprocess_failure_preserves_old_data_and_sets_failed(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    # 1. Create Collection
    col = Collection(user_id=user_id, name="Reprocess Error Test", description="Checking failure rollback")
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    # 2. Upload document
    content = b"Original content for testing reprocess failure rollback."
    doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="test_reprocess_fail.txt",
        content_bytes=content,
        user_id=user_id,
    )
    assert doc.status == "PROCESSED"
    initial_chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    assert initial_chunks > 0
    initial_vectors = vector_store_service.count(col.id)
    assert initial_vectors > 0

    # 3. Simulate failure during embedding in reprocess_document
    with patch("app.services.document_service.embedding_service.embed_texts", side_effect=RuntimeError("Embedding service down")):
        with pytest.raises(RuntimeError, match="Embedding service down"):
            document_service.reprocess_document(db=db_session, document_id=doc.id)

    # 4. Verify document status is set to FAILED
    db_session.refresh(doc)
    assert doc.status == "FAILED"
    assert "Embedding service down" in (doc.error_message or "")

    # 5. Verify existing vectors and chunks were preserved
    chunks_after_fail = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    assert chunks_after_fail == initial_chunks

    vectors_after_fail = vector_store_service.count(col.id)
    assert vectors_after_fail == initial_vectors

    # Cleanup
    document_service.delete_document(db_session, doc.id)
    db_session.delete(col)
    db_session.commit()

def test_update_failure_preserves_old_data_and_cleans_up_new_version(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    # 1. Create Collection
    col = Collection(user_id=user_id, name="Update Error Test", description="Checking update failure rollback")
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    # 2. Upload document v1
    content_v1 = b"Version 1 original content for update failure rollback test."
    doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="test_update_fail.txt",
        content_bytes=content_v1,
        user_id=user_id,
    )
    assert doc.status == "PROCESSED"
    assert doc.current_version == 1
    initial_vectors = vector_store_service.count(col.id)
    assert initial_vectors > 0

    # 3. Simulate failure during embedding in update_document
    content_v2 = b"Version 2 candidate content that will fail during embedding."
    with patch("app.services.document_service.embedding_service.embed_texts", side_effect=RuntimeError("GPU OOM")):
        with pytest.raises(RuntimeError, match="GPU OOM"):
            document_service.update_document(
                db=db_session,
                document_id=doc.id,
                filename="test_update_fail.txt",
                new_content_bytes=content_v2,
            )

    # 4. Verify document status is set to FAILED
    db_session.refresh(doc)
    assert doc.status == "FAILED"
    assert "GPU OOM" in (doc.error_message or "")

    # 5. Verify DocumentVersion v2 was deleted and v1 was reactivated
    v2 = db_session.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id,
        DocumentVersion.version_number == 2,
    ).first()
    assert v2 is None

    v1 = db_session.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id,
        DocumentVersion.version_number == 1,
    ).first()
    assert v1 is not None
    assert v1.is_active is True

    # 6. Verify existing vectors in ChromaDB were preserved
    vectors_after_fail = vector_store_service.count(col.id)
    assert vectors_after_fail == initial_vectors

    # Cleanup
    document_service.delete_document(db_session, doc.id)
    db_session.delete(col)
    db_session.commit()

def test_upload_retry_failed_document_reuses_record_without_duplicates(db_session):
    user_id = UserRepository(db_session).get_or_create_default().id
    col = Collection(user_id=user_id, name="Retry Test Col", description="Checking duplicate prevention on retry")
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    content = b"Content for failed upload retry testing."

    # 1. First upload attempt fails during embedding
    with patch("app.services.document_service.embedding_service.embed_texts", side_effect=RuntimeError("Transient network failure")):
        with pytest.raises(RuntimeError, match="Transient network failure"):
            document_service.upload_and_process(
                db=db_session,
                collection_id=col.id,
                filename="retry_test.txt",
                content_bytes=content,
                user_id=user_id,
            )

    # Verify 1 document exists in FAILED status
    docs = db_session.query(Document).filter(Document.collection_id == col.id).all()
    assert len(docs) == 1
    failed_doc = docs[0]
    assert failed_doc.status == "FAILED"
    first_doc_id = failed_doc.id

    # 2. Retry upload with the exact same content (same content hash) without patch
    retried_doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="retry_test.txt",
        content_bytes=content,
        user_id=user_id,
    )

    # Verify the document ID was reused and no duplicate row was created
    assert retried_doc.id == first_doc_id
    assert retried_doc.status == "PROCESSED"

    total_docs = db_session.query(Document).filter(Document.collection_id == col.id).count()
    assert total_docs == 1

    # 3. Third upload with identical content returns the PROCESSED record immediately
    cached_doc = document_service.upload_and_process(
        db=db_session,
        collection_id=col.id,
        filename="retry_test.txt",
        content_bytes=content,
        user_id=user_id,
    )
    assert cached_doc.id == first_doc_id
    assert cached_doc.status == "PROCESSED"
    assert db_session.query(Document).filter(Document.collection_id == col.id).count() == 1

    # Cleanup
    document_service.delete_document(db_session, retried_doc.id)
    db_session.delete(col)
    db_session.commit()

