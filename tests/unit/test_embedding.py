import sys
from pathlib import Path
from unittest.mock import MagicMock

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.embedding import EmbeddingService

def test_pinned_local_backend():
    service = EmbeddingService(backend="local")
    assert service.backend == "local"
    assert service._chroma_ef is None

    embs = service.embed_texts(["hello world", "test query"])
    assert len(embs) == 2
    assert len(embs[0]) == 384
    assert len(embs[1]) == 384

    query_emb = service.embed_query("test query")
    assert len(query_emb) == 384
    # Query embedding matches texts embedding for identical text
    assert query_emb == embs[1]

def test_invalid_backend_raises_error():
    with pytest.raises(ValueError, match="Unknown embedding backend"):
        EmbeddingService(backend="unsupported_backend")

def test_chroma_backend_error_propagation(monkeypatch):
    service = EmbeddingService(backend="local")
    # Simulate a pinned backend that fails
    service.backend = "chroma"
    mock_ef = MagicMock(side_effect=Exception("ONNX model execution failed"))
    service._chroma_ef = mock_ef

    with pytest.raises(RuntimeError, match="Pinned 'chroma' embedding backend failed"):
        service.embed_texts(["test text"])
