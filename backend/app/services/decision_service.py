import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.decision import Decision, DecisionOption
from app.models.evidence_analysis import Evidence, AnalysisResult
from app.repositories.decision_repository import DecisionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import GoalRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.services.embedding import embedding_service, EmbeddingService
from app.services.vector_store import vector_store_service, VectorStoreService
from app.services.llm_service import llm_service, LLMService
from app.schemas.decision import (
    DecisionCreate,
    DecisionUpdate,
    DecisionOptionCreate,
    DecisionAnalysisResponse,
    OptionAnalysisItem,
)

logger = logging.getLogger(__name__)

class DecisionIntelligenceService:
    """
    Core Decision Intelligence engine for LifeOps AI.
    Handles decision creation, document evidence retrieval across ChromaDB,
    multi-option evaluation (match, strengths, weaknesses, gaps, constraints,
    goal alignment, evidence, confidence, recommendations), and result persistence.
    """

    def __init__(
        self,
        llm: LLMService = llm_service,
        vector_store: VectorStoreService = vector_store_service,
        embedding: EmbeddingService = embedding_service,
    ):
        self.llm = llm
        self.vector_store = vector_store
        self.embedding = embedding

    def create_decision(
        self,
        db: Session,
        user_id: str,
        data: DecisionCreate,
    ) -> Decision:
        user_repo = UserRepository(db)
        user = user_repo.get(user_id)
        if not user:
            user = user_repo.get_or_create_default()
            user_id = user.id

        decision = Decision(
            user_id=user_id,
            title=data.title,
            question=data.question,
            context_description=data.context_description,
            deadline=data.deadline,
            constraints=data.constraints or [],
            status="DRAFT",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        repo = DecisionRepository(db)

        # Link strategic goals
        if data.goal_ids:
            repo.set_goals(decision, data.goal_ids)

        # Add candidate options
        if data.options:
            for opt in data.options:
                repo.add_option(
                    decision_id=decision.id,
                    title=opt.title,
                    description=opt.description,
                    effort_estimate=opt.effort_estimate,
                )

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision.id,
            action="CREATED",
            details=f"Created decision '{decision.title}' with {len(data.options)} option(s)",
        )

        return repo.get_with_relations(decision.id, user_id)

    def get_decision(
        self,
        db: Session,
        decision_id: str,
        user_id: str,
    ) -> Optional[Decision]:
        repo = DecisionRepository(db)
        return repo.get_with_relations(decision_id, user_id)

    def list_decisions(
        self,
        db: Session,
        user_id: str,
        status_filter: Optional[str] = None,
    ) -> List[Decision]:
        repo = DecisionRepository(db)
        return repo.list_by_user(user_id, status_filter)

    def update_decision(
        self,
        db: Session,
        decision_id: str,
        user_id: str,
        data: DecisionUpdate,
    ) -> Optional[Decision]:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            return None

        if data.title is not None:
            decision.title = data.title
        if data.question is not None:
            decision.question = data.question
        if data.context_description is not None:
            decision.context_description = data.context_description
        if data.deadline is not None:
            decision.deadline = data.deadline
        if data.constraints is not None:
            decision.constraints = data.constraints
        if data.status is not None:
            decision.status = data.status
        if data.selected_option_id is not None:
            decision.selected_option_id = data.selected_option_id

        if data.goal_ids is not None:
            repo.set_goals(decision, data.goal_ids)

        db.commit()
        db.refresh(decision)

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision.id,
            action="UPDATED",
            details=f"Updated decision '{decision.title}'",
        )

        return repo.get_with_relations(decision.id, user_id)

    def delete_decision(
        self,
        db: Session,
        decision_id: str,
        user_id: str,
    ) -> bool:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            return False

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision.id,
            action="DELETED",
            details=f"Deleted decision '{decision.title}'",
        )

        return repo.delete(decision_id)

    def add_option(
        self,
        db: Session,
        decision_id: str,
        user_id: str,
        data: DecisionOptionCreate,
    ) -> DecisionOption:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            raise ValueError(f"Decision '{decision_id}' not found.")

        option = repo.add_option(
            decision_id=decision_id,
            title=data.title,
            description=data.description,
            effort_estimate=data.effort_estimate,
        )

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision_id,
            action="UPDATED",
            details=f"Added option '{option.title}' to decision '{decision.title}'",
        )

        return option

    def delete_option(
        self,
        db: Session,
        decision_id: str,
        option_id: str,
        user_id: str,
    ) -> bool:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            return False

        success = repo.delete_option(option_id)
        if success:
            activity_repo = ActivityLogRepository(db)
            activity_repo.log_activity(
                user_id=user_id,
                entity_type="DECISION",
                entity_id=decision_id,
                action="UPDATED",
                details=f"Deleted option '{option_id}' from decision '{decision.title}'",
            )
        return success

    def select_option(
        self,
        db: Session,
        decision_id: str,
        option_id: str,
        user_id: str,
    ) -> Optional[Decision]:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            return None

        # Verify option belongs to this decision
        opt = next((o for o in decision.options if o.id == option_id), None)
        if not opt:
            raise ValueError(f"Option '{option_id}' does not belong to decision '{decision_id}'.")

        decision.selected_option_id = option_id
        decision.status = "DECIDED"
        db.commit()
        db.refresh(decision)

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision.id,
            action="DECIDED",
            details=f"Selected option '{opt.title}' for decision '{decision.title}'",
        )

        return repo.get_with_relations(decision_id, user_id)

    def analyze_decision(
        self,
        db: Session,
        decision_id: str,
        user_id: str,
    ) -> DecisionAnalysisResponse:
        repo = DecisionRepository(db)
        decision = repo.get_with_relations(decision_id, user_id)
        if not decision:
            raise ValueError(f"Decision '{decision_id}' not found.")

        if not decision.options:
            raise ValueError("Cannot analyze decision without at least one option.")

        # 1. Retrieve user's collections to search for evidence
        col_repo = CollectionRepository(db)
        collections = col_repo.list_by_user(user_id)

        # 2. Retrieve document evidence for each option
        options_context: List[Dict[str, Any]] = []

        for opt in decision.options:
            opt_evidence_chunks: List[Dict[str, Any]] = []
            search_query = f"{opt.title} {opt.description or ''} {decision.question}".strip()

            for col in collections:
                try:
                    q_emb = self.embedding.embed_query(search_query)
                    q_res = self.vector_store.query_vectors(
                        collection_name=col.id,
                        query_embeddings=[q_emb],
                        n_results=3,
                    )
                    docs_retrieved = q_res.get("documents", [[]])[0]
                    metas_retrieved = q_res.get("metadatas", [[]])[0]
                    dists_retrieved = q_res.get("distances", [[]])[0]

                    opt_keywords = [w for w in re.findall(r"\w+", opt.title.lower()) if len(w) > 2]
                    for d_text, meta, dist in zip(docs_retrieved, metas_retrieved, dists_retrieved):
                        sim = max(0.0, 1.0 - float(dist))
                        has_keyword = any(kw in d_text.lower() for kw in opt_keywords) if opt_keywords else False
                        if sim >= 0.18 or (has_keyword and sim >= 0.10):
                            chunk = {
                                "content": d_text,
                                "metadata": meta,
                                "similarity": round(sim, 3),
                                "collection_id": col.id,
                            }
                            opt_evidence_chunks.append(chunk)

                            # Persist Evidence record in database
                            ev_record = Evidence(
                                document_id=meta.get("document_id"),
                                chunk_id=meta.get("chunk_id"),
                                claim=f"Evidence for option '{opt.title}'",
                                extracted_text=d_text[:1000],
                                source_filename=meta.get("filename", "Document"),
                                page_number=meta.get("page_number", 1),
                                relevance_score=round(sim, 3),
                            )
                            db.add(ev_record)
                except Exception as e:
                    logger.warning(f"Error querying vector store for option {opt.id} in collection {col.id}: {e}")

            # Deduplicate chunks for this option by document content
            seen_texts = set()
            unique_chunks = []
            for ch in opt_evidence_chunks:
                txt_key = ch["content"][:100]
                if txt_key not in seen_texts:
                    seen_texts.add(txt_key)
                    unique_chunks.append(ch)

            options_context.append({
                "id": opt.id,
                "option_id": opt.id,
                "title": opt.title,
                "description": opt.description,
                "effort_estimate": opt.effort_estimate,
                "evidence_chunks": unique_chunks[:4],
            })

        # 3. Retrieve general evidence for the decision question + context
        general_evidence_chunks: List[Dict[str, Any]] = []
        gen_query = f"{decision.question} {decision.context_description or ''}".strip()
        for col in collections:
            try:
                g_emb = self.embedding.embed_query(gen_query)
                g_res = self.vector_store.query_vectors(
                    collection_name=col.id,
                    query_embeddings=[g_emb],
                    n_results=3,
                )
                g_docs = g_res.get("documents", [[]])[0]
                g_metas = g_res.get("metadatas", [[]])[0]
                g_dists = g_res.get("distances", [[]])[0]
                for d_text, meta, dist in zip(g_docs, g_metas, g_dists):
                    sim = max(0.0, 1.0 - float(dist))
                    if sim >= 0.18:
                        general_evidence_chunks.append({
                            "content": d_text,
                            "metadata": meta,
                            "similarity": round(sim, 3),
                            "collection_id": col.id,
                        })
            except Exception as e:
                logger.warning(f"Error querying general evidence in collection {col.id}: {e}")

        # 4. Assemble Decision Context
        decision_context = {
            "id": decision.id,
            "title": decision.title,
            "question": decision.question,
            "context_description": decision.context_description,
            "deadline": decision.deadline.isoformat() if decision.deadline else None,
            "constraints": decision.constraints or [],
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "importance": g.importance,
                    "status": g.status,
                }
                for g in decision.goals
            ],
        }

        # 5. Call LLM Service for Decision Intelligence
        analysis_raw = self.llm.generate_decision_analysis(
            decision_context=decision_context,
            options_context=options_context,
            general_evidence=general_evidence_chunks[:5],
        )

        # 6. Extract results & update option match scores
        options_analysis_data = analysis_raw.get("options_analysis", [])
        options_scores = {
            item["option_id"]: float(item["match"])
            for item in options_analysis_data
            if "option_id" in item and "match" in item
        }

        # 7. Persist AnalysisResult & update Decision status to ANALYZED
        analysis_result = repo.save_decision_analysis(
            decision=decision,
            recommendation=analysis_raw.get("recommendation", "Decision analysis complete."),
            confidence=analysis_raw.get("confidence", "MEDIUM"),
            reasoning_summary=analysis_raw.get("reasoning_summary", "Comparative analysis complete."),
            details_json=analysis_raw,
            options_scores=options_scores,
        )

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="DECISION",
            entity_id=decision.id,
            action="ANALYZED",
            details=f"Analyzed decision '{decision.title}' with {len(decision.options)} option(s)",
        )

        # 8. Return structured DecisionAnalysisResponse
        items = []
        for item in options_analysis_data:
            items.append(
                OptionAnalysisItem(
                    option_id=item.get("option_id", ""),
                    option_title=item.get("option_title", ""),
                    match=float(item.get("match", 50.0)),
                    strengths=item.get("strengths", []),
                    weaknesses=item.get("weaknesses", []),
                    gaps=item.get("gaps", []),
                    constraints=item.get("constraints", []),
                    goal_alignment=item.get("goal_alignment", ""),
                    evidence=item.get("evidence", []),
                    confidence=float(item.get("confidence", 0.9)),
                    recommendation=item.get("recommendation", "VIABLE ALTERNATIVE"),
                )
            )

        return DecisionAnalysisResponse(
            decision_id=decision.id,
            recommendation=analysis_result.recommendation,
            confidence=analysis_result.confidence,
            reasoning_summary=analysis_result.reasoning_summary,
            top_option_id=analysis_raw.get("top_option_id"),
            options_analysis=items,
            created_at=analysis_result.created_at or datetime.now(timezone.utc),
        )

decision_service = DecisionIntelligenceService()
