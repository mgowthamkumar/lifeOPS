import math
import hashlib
from typing import List, Optional
from app.core.config import settings

class EmbeddingService:
    """Provides semantic embedding generation with a pinned, consistent backend."""

    def __init__(self, backend: Optional[str] = None):
        self.backend = (backend or getattr(settings, "EMBEDDING_BACKEND", "local")).lower()
        self._chroma_ef = None

        if self.backend == "chroma":
            try:
                import chromadb.utils.embedding_functions as ef
                self._chroma_ef = ef.DefaultEmbeddingFunction()
            except Exception as e:
                raise RuntimeError(f"Failed to initialize pinned 'chroma' embedding backend: {e}") from e
        elif self.backend == "local":
            pass
        else:
            raise ValueError(f"Unknown embedding backend: '{self.backend}'. Supported backends: 'local', 'chroma'")

    def _local_embed(self, text: str, dimension: int = 384) -> List[float]:
        """
        Deterministic normalized token embedding for local deployment and testing.
        Computes L2-normalized vector over hashed words and bigrams.
        """
        vec = [0.0] * dimension
        words = text.lower().strip().split()
        if not words:
            vec[0] = 1.0
            return vec

        for word in words:
            idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % dimension
            vec[idx] += 1.0

        for i in range(len(words) - 1):
            bi = f"{words[i]}_{words[i+1]}"
            idx = int(hashlib.sha256(bi.encode("utf-8")).hexdigest(), 16) % dimension
            vec[idx] += 1.5

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of text strings using the pinned backend."""
        if not texts:
            return []

        if self.backend == "chroma":
            if self._chroma_ef is None:
                raise RuntimeError("Pinned 'chroma' embedding function is not initialized.")
            try:
                embeddings = self._chroma_ef(texts)
                return [list(e) for e in embeddings]
            except Exception as e:
                # Propagate error; never silently fallback to a different vector space
                raise RuntimeError(f"Pinned 'chroma' embedding backend failed during execution: {e}") from e

        # Pinned local backend
        return [self._local_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Generates single embedding vector for a search query using the pinned backend."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * 384

embedding_service = EmbeddingService()
