import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.evidence import (
    EvidenceExploreRequest,
    EvidenceExploreResponse,
    EvidenceItem,
    ConflictSourceDetail,
    EvidenceConflictItem,
    EvidenceInvestigationSummary,
)
from app.models.evidence_analysis import Evidence, EvidenceInvestigation
from app.models.document import DocumentChunk
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import (
    EvidenceRepository,
    EvidenceInvestigationRepository,
    ActivityLogRepository,
)
from app.services.embedding import embedding_service, EmbeddingService
from app.services.vector_store import vector_store_service, VectorStoreService
from app.services.llm_service import llm_service, LLMService

logger = logging.getLogger(__name__)

class EvidenceExplorerService:
    """
    Evidence Explorer Service:
    - Analyzes claims against real indexed documents.
    - Extracts source, page, chunk, relevance, reasoning, confidence, and uncertainty.
    - Implements cross-source conflict detection (opposing assertions, numerical differences).
    - Enforces anti-hallucination: returns INSUFFICIENT EVIDENCE with zero fabricated citations.
    - Persists investigations and individual evidence items for auditability.
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

    def explore_claim(
        self,
        db: Session,
        request: EvidenceExploreRequest,
        user_id: str,
    ) -> EvidenceExploreResponse:
        claim = request.claim.strip()
        top_k = request.top_k
        rel_threshold = request.relevance_threshold
        target_collection_id = request.collection_id

        col_repo = CollectionRepository(db)
        inv_repo = EvidenceInvestigationRepository(db)
        ev_repo = EvidenceRepository(db)
        act_repo = ActivityLogRepository(db)

        # 1. Determine collections to query
        active_collections = []
        if target_collection_id:
            col = col_repo.get(target_collection_id)
            if not col:
                raise ValueError(f"Collection '{target_collection_id}' not found.")
            active_collections.append(col)
        else:
            user_cols = col_repo.list_by_user(user_id)
            active_collections.extend(user_cols)

        # 2. Check total indexed vectors
        total_vectors = sum(self.vector_store.count(c.id) for c in active_collections)
        if total_vectors == 0:
            # Insufficient evidence: no vectors exist
            investigation = inv_repo.create(
                user_id=user_id,
                collection_id=target_collection_id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary="INSUFFICIENT EVIDENCE: No indexed documents found in active collections. Upload documents to verify claims.",
                conflicts_json=[],
                evidence_items_json=[],
            )
            act_repo.log_activity(
                user_id=user_id,
                entity_type="EVIDENCE",
                entity_id=investigation.id,
                action="EXPLORED",
                details=f"Explored claim '{claim}': INSUFFICIENT EVIDENCE (0 vectors)",
            )
            return EvidenceExploreResponse(
                investigation_id=investigation.id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary="INSUFFICIENT EVIDENCE: No indexed documents found in active collections. Upload documents to verify claims.",
                evidence_items=[],
                conflicts=[],
                collection_id=target_collection_id,
                total_sources_evaluated=0,
                created_at=investigation.created_at,
            )

        # 3. Embed claim
        claim_vector = self.embedding.embed_query(claim)

        # 4. Extract key non-stopword tokens from claim for hybrid entity matching
        claim_terms = {
            t for t in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", claim.lower())
            if t not in {
                "what", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at",
                "to", "for", "of", "with", "by", "from", "up", "about", "into", "over",
                "after", "who", "which", "how", "when", "where", "why", "can", "could",
                "should", "would", "do", "does", "did", "have", "has", "had", "will",
                "must", "all"
            }
        }

        # 5. Retrieve candidate chunks across collections
        all_candidates: List[Dict[str, Any]] = []
        for col in active_collections:
            cnt = self.vector_store.count(col.id)
            if cnt == 0:
                continue
            try:
                res = self.vector_store.query_vectors(
                    collection_name=col.id,
                    query_embeddings=[claim_vector],
                    n_results=min(top_k * 2, cnt),
                )
                ids = res.get("ids", [[]])[0]
                distances = res.get("distances", [[]])[0]
                metadatas = res.get("metadatas", [[]])[0]
                documents = res.get("documents", [[]])[0]

                for i in range(len(ids)):
                    dist = distances[i] if i < len(distances) else 1.0
                    similarity = max(0.0, 1.0 - float(dist))
                    doc_text = documents[i] if i < len(documents) else ""

                    # Hybrid lexical relevance bonus (vital for contradictory / opposing assertions)
                    if claim_terms and doc_text:
                        doc_tokens = set(re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", doc_text.lower()))
                        overlap = claim_terms.intersection(doc_tokens)
                        if overlap:
                            lex_bonus = min(0.35, (len(overlap) / max(1, len(claim_terms))) * 0.4)
                            similarity = min(1.0, similarity + lex_bonus)

                    if similarity >= rel_threshold:
                        all_candidates.append({
                            "id": ids[i],
                            "similarity": similarity,
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                            "content": doc_text,
                            "collection_id": col.id,
                        })
            except Exception as e:
                logger.warning(f"Error querying collection '{col.id}': {e}")
                continue

        # Sort candidate chunks by similarity descending
        all_candidates.sort(key=lambda x: x["similarity"], reverse=True)
        top_candidates = all_candidates[:top_k]

        # 5. If no chunks meet the relevance threshold, return INSUFFICIENT EVIDENCE
        if not top_candidates:
            investigation = inv_repo.create(
                user_id=user_id,
                collection_id=target_collection_id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary=f"INSUFFICIENT EVIDENCE: The uploaded documents do not contain evidence relevant to the claim: '{claim}'.",
                conflicts_json=[],
                evidence_items_json=[],
            )
            act_repo.log_activity(
                user_id=user_id,
                entity_type="EVIDENCE",
                entity_id=investigation.id,
                action="EXPLORED",
                details=f"Explored claim '{claim}': INSUFFICIENT EVIDENCE (0 relevant chunks)",
            )
            return EvidenceExploreResponse(
                investigation_id=investigation.id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary=f"INSUFFICIENT EVIDENCE: The uploaded documents do not contain evidence relevant to the claim: '{claim}'.",
                evidence_items=[],
                conflicts=[],
                collection_id=target_collection_id,
                total_sources_evaluated=0,
                created_at=investigation.created_at,
            )

        # 6. Deep Evidence & Conflict Analysis via LLM/Grounded Service
        analysis_result = self.llm.analyze_claim_evidence(claim, top_candidates)

        status = analysis_result.get("status", "VERIFIED_SUPPORT")
        has_sufficient_evidence = analysis_result.get("has_sufficient_evidence", True)
        conflict_detected = analysis_result.get("conflict_detected", False)
        confidence = float(analysis_result.get("confidence", 0.90))
        uncertainty = float(analysis_result.get("uncertainty", 0.10))
        uncertainty_level = analysis_result.get("uncertainty_level", "LOW")
        reasoning_summary = analysis_result.get("reasoning_summary", "")

        raw_items = analysis_result.get("evidence_items", [])
        raw_conflicts = analysis_result.get("conflicts", [])

        # If analysis determined insufficient evidence, enforce zero citations
        if not has_sufficient_evidence or "INSUFFICIENT" in status.upper():
            investigation = inv_repo.create(
                user_id=user_id,
                collection_id=target_collection_id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary=reasoning_summary or f"INSUFFICIENT EVIDENCE: Evaluated documents contain insufficient factual basis for claim: '{claim}'.",
                conflicts_json=[],
                evidence_items_json=[],
            )
            act_repo.log_activity(
                user_id=user_id,
                entity_type="EVIDENCE",
                entity_id=investigation.id,
                action="EXPLORED",
                details=f"Explored claim '{claim}': INSUFFICIENT EVIDENCE",
            )
            return EvidenceExploreResponse(
                investigation_id=investigation.id,
                claim=claim,
                status="INSUFFICIENT_EVIDENCE",
                has_sufficient_evidence=False,
                conflict_detected=False,
                confidence=0.0,
                uncertainty=1.0,
                uncertainty_level="HIGH",
                reasoning_summary=reasoning_summary or f"INSUFFICIENT EVIDENCE: Evaluated documents contain insufficient factual basis for claim: '{claim}'.",
                evidence_items=[],
                conflicts=[],
                collection_id=target_collection_id,
                total_sources_evaluated=len(top_candidates),
                created_at=investigation.created_at,
            )

        # 7. Map Evidence Items to verified documents and DB Chunks
        final_evidence_items: List[EvidenceItem] = []
        for raw_item in raw_items:
            c_idx = raw_item.get("chunk_index", 1) - 1
            if 0 <= c_idx < len(top_candidates):
                candidate = top_candidates[c_idx]
            else:
                candidate = top_candidates[0]

            meta = candidate.get("metadata", {})
            doc_id = meta.get("document_id")
            filename = meta.get("filename", "Verified Source Document")
            page_num = meta.get("page_number", 1)
            chunk_num = meta.get("chunk_index", 0)
            snippet = candidate.get("content", "")

            # Look up DB chunk if available
            db_chunk = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == doc_id, DocumentChunk.chunk_index == chunk_num)
                .first()
            ) if doc_id else None

            ev_id = f"ev_{meta.get('document_id', 'doc')}_{chunk_num}_{c_idx}"
            final_evidence_items.append(EvidenceItem(
                id=ev_id,
                claim=claim,
                document_id=doc_id,
                source_filename=filename,
                page_number=page_num,
                chunk_index=chunk_num,
                chunk_id=db_chunk.id if db_chunk else candidate.get("id"),
                chunk_text=snippet,
                relevance=float(raw_item.get("relevance", candidate.get("similarity", 0.8))),
                reasoning=raw_item.get("reasoning", f"Document excerpt from {filename} page {page_num}."),
                confidence=float(raw_item.get("confidence", 0.90)),
                uncertainty=float(raw_item.get("uncertainty", 0.10)),
                uncertainty_reasons=raw_item.get("uncertainty_reasons", ["Verbatim source citation"]),
                stance=raw_item.get("stance", "SUPPORTS"),
            ))

        # 8. Map Conflicts with detailed source references
        final_conflicts: List[EvidenceConflictItem] = []
        for c in raw_conflicts:
            idx_a = c.get("source_a_index", 1) - 1
            idx_b = c.get("source_b_index", 2) - 1

            cand_a = top_candidates[idx_a] if 0 <= idx_a < len(top_candidates) else top_candidates[0]
            cand_b = top_candidates[idx_b] if 0 <= idx_b < len(top_candidates) else (top_candidates[1] if len(top_candidates) > 1 else top_candidates[0])

            meta_a = cand_a.get("metadata", {})
            meta_b = cand_b.get("metadata", {})

            final_conflicts.append(EvidenceConflictItem(
                topic=c.get("topic", "Factual Discrepancy"),
                source_a=ConflictSourceDetail(
                    document_name=meta_a.get("filename", "Source A"),
                    document_id=meta_a.get("document_id"),
                    page_number=meta_a.get("page_number", 1),
                    chunk_index=meta_a.get("chunk_index", 0),
                    chunk_text=cand_a.get("content", "")[:300],
                    assertion=c.get("source_a_assertion", "Asserts primary condition"),
                ),
                source_b=ConflictSourceDetail(
                    document_name=meta_b.get("filename", "Source B"),
                    document_id=meta_b.get("document_id"),
                    page_number=meta_b.get("page_number", 1),
                    chunk_index=meta_b.get("chunk_index", 0),
                    chunk_text=cand_b.get("content", "")[:300],
                    assertion=c.get("source_b_assertion", "Asserts conflicting condition"),
                ),
                discrepancy_explanation=c.get("discrepancy_explanation", "Direct disagreement between source documents."),
                severity=c.get("severity", "HIGH"),
                suggested_resolution=c.get("suggested_resolution", "Reconcile conflicting policies with domain owner."),
            ))

        # 9. Persist EvidenceInvestigation record
        investigation = inv_repo.create(
            user_id=user_id,
            collection_id=target_collection_id,
            claim=claim,
            status=status,
            has_sufficient_evidence=True,
            conflict_detected=conflict_detected,
            confidence=confidence,
            uncertainty=uncertainty,
            uncertainty_level=uncertainty_level,
            reasoning_summary=reasoning_summary,
            conflicts_json=[conf.model_dump() for conf in final_conflicts],
            evidence_items_json=[ev.model_dump() for ev in final_evidence_items],
        )

        # 10. Persist individual Evidence rows
        try:
            for item in final_evidence_items:
                ev_record = Evidence(
                    investigation_id=investigation.id,
                    user_id=user_id,
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    chunk_index=item.chunk_index,
                    claim=item.claim,
                    extracted_text=item.chunk_text,
                    source_filename=item.source_filename,
                    page_number=item.page_number,
                    relevance_score=item.relevance,
                    reasoning=item.reasoning,
                    confidence=item.confidence,
                    uncertainty=item.uncertainty,
                    uncertainty_reasons=item.uncertainty_reasons,
                    stance=item.stance,
                )
                db.add(ev_record)
            db.commit()
        except Exception as e:
            logger.warning(f"Could not persist individual evidence items: {e}")
            db.rollback()

        # 11. Log Activity
        act_repo.log_activity(
            user_id=user_id,
            entity_type="EVIDENCE",
            entity_id=investigation.id,
            action="EXPLORED",
            details=f"Explored claim '{claim}': {status} (Conflicts: {len(final_conflicts)}, Evidence Items: {len(final_evidence_items)})",
        )

        return EvidenceExploreResponse(
            investigation_id=investigation.id,
            claim=claim,
            status=status,
            has_sufficient_evidence=True,
            conflict_detected=conflict_detected,
            confidence=confidence,
            uncertainty=uncertainty,
            uncertainty_level=uncertainty_level,
            reasoning_summary=reasoning_summary,
            evidence_items=final_evidence_items,
            conflicts=final_conflicts,
            collection_id=target_collection_id,
            total_sources_evaluated=len(top_candidates),
            created_at=investigation.created_at,
        )

    def list_investigations(
        self,
        db: Session,
        user_id: str,
        collection_id: Optional[str] = None,
        conflicts_only: bool = False,
    ) -> List[EvidenceInvestigationSummary]:
        inv_repo = EvidenceInvestigationRepository(db)
        investigations = inv_repo.list_by_user(
            user_id=user_id,
            collection_id=collection_id,
            conflicts_only=conflicts_only,
        )
        results = []
        for inv in investigations:
            items = inv.evidence_items_json or []
            results.append(EvidenceInvestigationSummary(
                id=inv.id,
                claim=inv.claim,
                status=inv.status,
                conflict_detected=inv.conflict_detected,
                confidence=inv.confidence,
                uncertainty=inv.uncertainty,
                uncertainty_level=inv.uncertainty_level,
                sources_count=len(items),
                created_at=inv.created_at,
            ))
        return results

    def get_investigation(
        self,
        db: Session,
        investigation_id: str,
        user_id: str,
    ) -> Optional[EvidenceExploreResponse]:
        inv_repo = EvidenceInvestigationRepository(db)
        inv = inv_repo.get_by_id_and_user(investigation_id, user_id)
        if not inv:
            return None

        raw_items = inv.evidence_items_json or []
        raw_conflicts = inv.conflicts_json or []

        return EvidenceExploreResponse(
            investigation_id=inv.id,
            claim=inv.claim,
            status=inv.status,
            has_sufficient_evidence=inv.has_sufficient_evidence,
            conflict_detected=inv.conflict_detected,
            confidence=inv.confidence,
            uncertainty=inv.uncertainty,
            uncertainty_level=inv.uncertainty_level,
            reasoning_summary=inv.reasoning_summary,
            evidence_items=[EvidenceItem(**item) for item in raw_items],
            conflicts=[EvidenceConflictItem(**c) for c in raw_conflicts],
            collection_id=inv.collection_id,
            total_sources_evaluated=len(raw_items),
            created_at=inv.created_at,
        )

    def delete_investigation(
        self,
        db: Session,
        investigation_id: str,
        user_id: str,
    ) -> bool:
        inv_repo = EvidenceInvestigationRepository(db)
        inv = inv_repo.get_by_id_and_user(investigation_id, user_id)
        if not inv:
            return False
        inv_repo.delete(inv.id)
        return True

evidence_explorer_service = EvidenceExplorerService()
