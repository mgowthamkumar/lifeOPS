import sys
from pathlib import Path
import tempfile
import shutil

# Add backend directory to sys.path
backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.vector_store import VectorStoreService

@pytest.fixture
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_vector_store_crud_and_query(temp_chroma_dir):
    service = VectorStoreService(persist_directory=temp_chroma_dir)
    assert service.is_healthy() is True

    col_name = "test_career_collection"
    
    # 1. Prepare real test embeddings (e.g. 4-dimensional vectors for testing)
    test_ids = ["chunk_1", "chunk_2", "chunk_3"]
    # Chunk 1 and Chunk 2 are similar (direction [1, 0, 0, 0]), Chunk 3 is orthogonal [0, 1, 0, 0]
    test_embeddings = [
        [0.98, 0.05, 0.02, 0.01],
        [0.95, 0.08, 0.01, 0.02],
        [0.02, 0.99, 0.01, 0.01],
    ]
    test_documents = [
        "Python and machine learning skills are mandatory for AI roles.",
        "Deep learning and agent frameworks are required for advanced AI.",
        "Corporate accounting principles and financial balance sheet rules.",
    ]
    test_metadatas = [
        {"document_id": "doc_ai_1", "page": 1, "topic": "ai"},
        {"document_id": "doc_ai_1", "page": 2, "topic": "ai"},
        {"document_id": "doc_finance_1", "page": 1, "topic": "finance"},
    ]

    # 2. Insert vectors
    service.add_chunks(
        collection_name=col_name,
        ids=test_ids,
        embeddings=test_embeddings,
        documents=test_documents,
        metadatas=test_metadatas,
    )
    assert service.count(col_name) == 3

    # 3. Query with a vector close to Chunk 1 & 2
    query_vector = [[0.99, 0.01, 0.01, 0.01]]
    results = service.query_vectors(
        collection_name=col_name,
        query_embeddings=query_vector,
        n_results=2,
    )
    assert len(results["ids"][0]) == 2
    assert results["ids"][0][0] in ["chunk_1", "chunk_2"]
    assert "Python" in results["documents"][0][0] or "Deep learning" in results["documents"][0][0]

    # 4. Query with metadata filtering
    filtered_results = service.query_vectors(
        collection_name=col_name,
        query_embeddings=query_vector,
        n_results=5,
        where_metadata={"topic": "finance"},
    )
    assert len(filtered_results["ids"][0]) == 1
    assert filtered_results["ids"][0][0] == "chunk_3"

    # 5. Delete specific chunk by ID
    service.delete_chunks(col_name, ids=["chunk_3"])
    assert service.count(col_name) == 2

    # 6. Delete by document ID
    service.delete_by_document(col_name, document_id="doc_ai_1")
    assert service.count(col_name) == 0

def test_vector_store_persistence_after_restart(temp_chroma_dir):
    col_name = "persistent_test_col"

    # Session 1: insert vector into persistent ChromaDB
    service1 = VectorStoreService(persist_directory=temp_chroma_dir)
    service1.add_chunks(
        collection_name=col_name,
        ids=["persist_chunk_001"],
        embeddings=[[0.5, 0.5, 0.5, 0.5]],
        documents=["This knowledge persists across process restarts."],
        metadatas=[{"doc_id": "persist_doc", "version": 1}],
    )
    assert service1.count(col_name) == 1
    del service1  # Drop client reference

    # Session 2: re-initialize VectorStoreService on the SAME directory
    service2 = VectorStoreService(persist_directory=temp_chroma_dir)
    assert service2.count(col_name) == 1

    # Query to verify data retrieved accurately
    res = service2.query_vectors(
        collection_name=col_name,
        query_embeddings=[[0.5, 0.5, 0.5, 0.5]],
        n_results=1,
    )
    assert res["ids"][0][0] == "persist_chunk_001"
    assert "This knowledge persists" in res["documents"][0][0]
    assert res["metadatas"][0][0]["doc_id"] == "persist_doc"
