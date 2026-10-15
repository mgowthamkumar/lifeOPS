import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Manages persistent ChromaDB vector storage."""

    def __init__(self, persist_directory: Optional[Path] = None):
        if persist_directory is None:
            self.persist_directory = settings.resolve_path(settings.CHROMA_PERSIST_DIRECTORY)
        else:
            self.persist_directory = Path(persist_directory)
        
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _sanitize_collection_name(self, name: str) -> str:
        """ChromaDB collection names must be 3-63 characters, start/end alphanumeric, no consecutive periods."""
        sanitized = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        if len(sanitized) < 3:
            sanitized = f"col_{sanitized}".ljust(3, "_")
        return sanitized[:63]

    def get_or_create_collection(self, collection_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Retrieve existing collection or create a new one."""
        clean_name = self._sanitize_collection_name(collection_name)
        return self.client.get_or_create_collection(
            name=clean_name,
            metadata=metadata or {"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Insert or update vector embeddings with metadata into ChromaDB."""
        collection = self.get_or_create_collection(collection_name)
        # ChromaDB requires non-None metadatas or omits them
        safe_metadatas = metadatas if metadatas is not None else [{} for _ in ids]
        
        # Flatten complex types in metadata for ChromaDB compatibility (strings, ints, floats, bools only)
        cleaned_metadatas = []
        for meta in safe_metadatas:
            cleaned = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                else:
                    cleaned[k] = str(v)
            cleaned_metadatas.append(cleaned)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=cleaned_metadatas,
        )

    def query_vectors(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform semantic search using query embeddings and optional metadata filter."""
        empty_res = {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
        try:
            collection = self.get_or_create_collection(collection_name)
            if collection.count() == 0:
                return empty_res
            query_args = {
                "query_embeddings": query_embeddings,
                "n_results": min(n_results, collection.count()),
            }
            if where_metadata:
                query_args["where"] = where_metadata
            return collection.query(**query_args)
        except Exception as e:
            logger.warning(f"ChromaDB query failed on collection '{collection_name}': {e}")
            return empty_res

    def delete_chunks(self, collection_name: str, ids: List[str]) -> None:
        """Delete specific chunks by ID."""
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=ids)

    def delete_by_document(self, collection_name: str, document_id: str) -> None:
        """Delete all chunks belonging to a specific document."""
        collection = self.get_or_create_collection(collection_name)
        collection.delete(where={"document_id": document_id})

    def count(self, collection_name: str) -> int:
        """Get chunk count for a collection."""
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    def delete_collection(self, collection_name: str) -> None:
        """Delete an entire collection."""
        clean_name = self._sanitize_collection_name(collection_name)
        try:
            self.client.delete_collection(name=clean_name)
        except Exception:
            pass

    def is_healthy(self) -> bool:
        """Check if persistent ChromaDB client is responsive."""
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False

# Singleton instance
vector_store_service = VectorStoreService()
