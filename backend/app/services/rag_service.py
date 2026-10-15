import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, RAGSource
from app.models.evidence_analysis import Evidence
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.services.embedding import embedding_service, EmbeddingService
from app.services.vector_store import vector_store_service, VectorStoreService
from app.services.llm_service import llm_service, LLMService

logger = logging.getLogger(__name__)

class RAGService:
    """
    Orchestrates the real Retrieval-Augmented Generation (RAG) pipeline:
    Question -> Query Embedding -> ChromaDB Retrieval -> Relevance Filtering ->
    Context Assembly -> Grounded LLM Generation -> Source Citations & Persistence.
    """

    def __init__(
        self,
        vector_store: VectorStoreService = vector_store_service,
        embedding: EmbeddingService = embedding_service,
        llm: LLMService = llm_service,
    ):
        self.vector_store = vector_store
        self.embedding = embedding
        self.llm = llm

    def query(
        self,
        db: Session,
        collection_id: str,
        question: str,
        top_k: int = 5,
        relevance_threshold: float = 0.35,
        user_id: Optional[str] = None,
    ) -> RAGQueryResponse:
        # 1. Validate collection existence
        col_repo = CollectionRepository(db)
        collection = col_repo.get(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found.")

        # 2. Check total indexed vectors
        total_vectors = self.vector_store.count(collection_id)
        if total_vectors == 0:
            return RAGQueryResponse(
                question=question,
                answer="INSUFFICIENT EVIDENCE: This collection does not contain any indexed documents.",
                has_sufficient_evidence=False,
                confidence_score=0.0,
                sources=[],
                collection_id=collection_id,
                retrieval_count=0,
                model_used="none",
                created_at=datetime.now(timezone.utc),
            )

        # 3. Generate query vector embedding
        query_vector = self.embedding.embed_query(question)

        # 4. Retrieve candidate chunks from persistent ChromaDB
        query_result = self.vector_store.query_vectors(
            collection_name=collection_id,
            query_embeddings=[query_vector],
            n_results=top_k,
        )

        ids = query_result.get("ids", [[]])[0]
        distances = query_result.get("distances", [[]])[0]
        metadatas = query_result.get("metadatas", [[]])[0]
        documents = query_result.get("documents", [[]])[0]

        # 5. Calculate cosine similarity and filter by relevance threshold
        relevant_chunks: List[Dict[str, Any]] = []
        for i in range(len(ids)):
            dist = distances[i] if i < len(distances) else 1.0
            # For cosine distance, similarity = 1 - distance
            similarity = max(0.0, 1.0 - float(dist))

            if similarity >= relevance_threshold:
                relevant_chunks.append({
                    "id": ids[i],
                    "similarity": round(similarity, 4),
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "content": documents[i] if i < len(documents) else "",
                })

        # 6. If no chunks meet the relevance threshold, return INSUFFICIENT EVIDENCE immediately
        log_repo = ActivityLogRepository(db)
        if not relevant_chunks:
            log_repo.log_activity(
                entity_type="RAG_QUERY",
                action="INSUFFICIENT_EVIDENCE",
                user_id=user_id,
                details=f"Query '{question}' yielded 0 chunks meeting relevance threshold ({relevance_threshold}).",
            )
            return RAGQueryResponse(
                question=question,
                answer="INSUFFICIENT EVIDENCE: The uploaded documents in this collection do not contain sufficient evidence to answer this question.",
                has_sufficient_evidence=False,
                confidence_score=0.0,
                sources=[],
                collection_id=collection_id,
                retrieval_count=0,
                model_used="none",
                created_at=datetime.now(timezone.utc),
            )

        # 7. Pass context to LLM for grounded answer generation
        llm_output = self.llm.generate_grounded_answer(
            question=question,
            context_chunks=relevant_chunks,
        )

        has_sufficient_evidence = llm_output.get("has_sufficient_evidence", True)
        answer_text = llm_output.get("answer", "")
        confidence = float(llm_output.get("confidence", 0.0))
        model_name = llm_output.get("model", "unknown")

        # Double check: if answer states INSUFFICIENT EVIDENCE, enforce empty sources
        if not has_sufficient_evidence or "INSUFFICIENT EVIDENCE" in answer_text.upper():
            has_sufficient_evidence = False
            sources = []
            confidence = 0.0
            log_repo.log_activity(
                entity_type="RAG_QUERY",
                action="INSUFFICIENT_EVIDENCE",
                user_id=user_id,
                details=f"Query '{question}' determined insufficient evidence by model {model_name}.",
            )
        else:
            # 8. Map verified sources
            sources = []
            for c in relevant_chunks:
                meta = c["metadata"]
                sources.append(RAGSource(
                    document_id=str(meta.get("document_id", "")),
                    document_name=str(meta.get("filename", "Unknown Document")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    page_number=int(meta.get("page_number", 1)) if meta.get("page_number") is not None else None,
                    version=int(meta.get("version", 1)),
                    similarity_score=float(c["similarity"]),
                    content_snippet=c["content"][:280] + ("..." if len(c["content"]) > 280 else ""),
                ))

            # 9. Persist evidence items in relational database
            try:
                for c in relevant_chunks[:5]:
                    meta = c["metadata"]
                    ev = Evidence(
                        document_id=meta.get("document_id"),
                        source_filename=meta.get("filename", "Unknown"),
                        page_number=meta.get("page_number", 1),
                        relevance_score=float(c["similarity"]),
                        claim=question[:200],
                        extracted_text=c["content"][:400],
                    )
                    db.add(ev)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not persist evidence records: {e}")
                db.rollback()

            log_repo.log_activity(
                entity_type="RAG_QUERY",
                action="ANSWERED",
                user_id=user_id,
                details=f"Grounded answer generated for '{question}' from {len(sources)} source chunk(s).",
            )

        return RAGQueryResponse(
            question=question,
            answer=answer_text,
            has_sufficient_evidence=has_sufficient_evidence,
            confidence_score=confidence,
            sources=sources,
            collection_id=collection_id,
            retrieval_count=len(relevant_chunks),
            model_used=model_name,
            created_at=datetime.now(timezone.utc),
        )

rag_service = RAGService()
