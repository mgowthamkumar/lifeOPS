import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.task_goal import Task, Goal
from app.models.action_plan import ActionPlan
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import TaskRepository, GoalRepository
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.services.embedding import embedding_service, EmbeddingService
from app.services.vector_store import vector_store_service, VectorStoreService
from app.services.llm_service import llm_service, LLMService

logger = logging.getLogger(__name__)

class ActionPlanner:
    """
    Connects Tasks, Goals, User Context, Documents, RAG, and Gemini into an explainable,
    deterministic daily action planning intelligence system.
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

    def plan_day(
        self,
        db: Session,
        user_id: str,
        query: str = "What should I do today?",
        available_minutes: Optional[int] = None,
        focus_areas: Optional[List[str]] = None,
        custom_constraints: Optional[Dict[str, Any]] = None,
    ) -> ActionPlan:
        # 1. Resolve User and Context Constraints
        user_repo = UserRepository(db)
        user = user_repo.get(user_id)
        if not user:
            user = user_repo.get_or_create_default()
            user_id = user.id

        user_context = dict(user.context or {})
        eff_available_minutes = (
            available_minutes
            if available_minutes is not None
            else user_context.get("available_minutes", 480)
        )
        eff_focus_areas = (
            focus_areas
            if focus_areas is not None
            else user_context.get("focus_areas", [])
        )
        merged_constraints = {
            "available_minutes": eff_available_minutes,
            "focus_areas": eff_focus_areas,
            **(custom_constraints or {}),
        }

        # 2. Retrieve Active Tasks (TODO, IN_PROGRESS)
        task_repo = TaskRepository(db)
        all_tasks = task_repo.list_by_user(user_id)
        active_tasks = [t for t in all_tasks if t.status in ["TODO", "IN_PROGRESS"]]

        # 3. Retrieve Goal Information
        goal_repo = GoalRepository(db)
        goals_map = {g.id: g for g in goal_repo.list_by_user(user_id)}

        # If no active tasks exist, return an empty plan explaining the state
        if not active_tasks:
            plan_repo = ActionPlanRepository(db)
            plan = plan_repo.create_plan(
                user_id=user_id,
                query=query,
                summary="No active or pending tasks found in your system. Create tasks linked to your strategic goals to generate an action plan.",
                total_estimated_minutes=0,
                available_minutes_constraint=eff_available_minutes,
                user_context_snapshot=merged_constraints,
                items_data=[],
                status="ACTIVE",
            )
            return plan

        # 4. RAG Retrieval for Document Evidence & Candidate Context Assembly
        candidate_tasks: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for task in active_tasks:
            parent_goal = goals_map.get(task.goal_id) if task.goal_id else None
            goal_importance = parent_goal.importance if parent_goal else "MEDIUM"
            goal_title = parent_goal.title if parent_goal else None
            goal_progress = parent_goal.progress if parent_goal else 0.0

            evidence_text: Optional[str] = None
            evidence_doc_name: Optional[str] = None

            # 4a. Check linked documents
            if task.documents:
                for doc in task.documents:
                    if doc.collection_id:
                        try:
                            q_emb = self.embedding.embed_query(f"{task.title} {task.description or ''}")
                            q_res = self.vector_store.query_vectors(
                                collection_name=doc.collection_id,
                                query_embeddings=[q_emb],
                                n_results=2,
                            )
                            docs_retrieved = q_res.get("documents", [[]])[0]
                            metas_retrieved = q_res.get("metadatas", [[]])[0]
                            dists_retrieved = q_res.get("distances", [[]])[0]

                            for d_text, meta, dist in zip(docs_retrieved, metas_retrieved, dists_retrieved):
                                sim = max(0.0, 1.0 - float(dist))
                                if sim >= 0.30 and meta.get("document_id") == doc.id:
                                    snippet = d_text.strip().replace("\n", " ")
                                    if len(snippet) > 160:
                                        snippet = snippet[:157] + "..."
                                    page_num = meta.get("page_number", 1)
                                    evidence_text = f"[Doc: {doc.filename}, Page {page_num}] \"{snippet}\""
                                    evidence_doc_name = doc.filename
                                    break
                        except Exception as e:
                            logger.warning(f"Error querying vector store for task {task.id}: {e}")

                    if evidence_text:
                        break

                if not evidence_text:
                    evidence_doc_name = task.documents[0].filename
                    evidence_text = f"[Doc: {evidence_doc_name}] Grounded in uploaded document '{evidence_doc_name}'"

            # 4b. If no linked doc, check collections for matching evidence
            if not evidence_text:
                try:
                    col_repo = CollectionRepository(db)
                    cols = col_repo.list_by_user(user_id)
                    for col in cols[:3]:
                        q_emb = self.embedding.embed_query(task.title)
                        q_res = self.vector_store.query_vectors(
                            collection_name=col.id,
                            query_embeddings=[q_emb],
                            n_results=1,
                        )
                        docs_ret = q_res.get("documents", [[]])[0]
                        metas_ret = q_res.get("metadatas", [[]])[0]
                        dists_ret = q_res.get("distances", [[]])[0]
                        if docs_ret and dists_ret:
                            sim = max(0.0, 1.0 - float(dists_ret[0]))
                            if sim >= 0.45:
                                fname = metas_ret[0].get("filename", "Knowledge Base")
                                snippet = docs_ret[0].strip().replace("\n", " ")[:150]
                                evidence_text = f"[Doc: {fname}] \"{snippet}...\""
                                break
                except Exception:
                    pass

            # 5. Deterministic Scoring Algorithm ("No random prioritization")
            score = self._calculate_task_score(task, parent_goal, now, eff_focus_areas, has_evidence=bool(evidence_text))

            candidate_tasks.append({
                "task_id": task.id,
                "goal_id": task.goal_id,
                "title": task.title,
                "description": task.description or "",
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "priority": task.priority,
                "estimated_duration_minutes": task.estimated_duration_minutes or 30,
                "category": task.category or "General",
                "goal_title": goal_title,
                "goal_importance": goal_importance,
                "goal_progress": goal_progress,
                "evidence_text": evidence_text,
                "evidence_doc": evidence_doc_name,
                "score": score,
            })

        # 6. Sort candidate tasks strictly by deterministic score descending
        # Secondary keys: duration ascending (easier completions first when tied)
        candidate_tasks.sort(
            key=lambda x: (
                x["score"],
                -(x["estimated_duration_minutes"]) if x["score"] > 50 else x["estimated_duration_minutes"],
            ),
            reverse=True,
        )

        # 7. Invoke Gemini / LLM for Structured Synthesis and Grounding
        plan_output = self.llm.generate_action_plan(
            query=query,
            tasks_context=candidate_tasks,
            constraints=merged_constraints,
        )

        raw_items = plan_output.get("items", [])
        plan_summary = plan_output.get("summary", "")

        # 8. Post-process and ensure strictly aligned items
        persisted_items_data: List[Dict[str, Any]] = []
        total_time_mins = 0

        # If LLM returned valid items, map them; otherwise use deterministic fallback items
        if raw_items:
            for idx, item in enumerate(raw_items, start=1):
                prio_num = int(item.get("priority", idx))
                prio_lbl = item.get("priority_label") or f"#{prio_num} - {candidate_tasks[idx-1]['priority'] if idx-1 < len(candidate_tasks) else 'MEDIUM'}"
                action_text = item.get("action", "")
                reason_text = item.get("reason", "")
                est_mins = int(item.get("estimated_minutes", 30))
                time_str = item.get("estimated_time") or f"{est_mins} minutes"
                ev_str = item.get("evidence") or (
                    candidate_tasks[idx-1].get("evidence_text")
                    if idx-1 < len(candidate_tasks) and candidate_tasks[idx-1].get("evidence_text")
                    else "Verified operational task requirement"
                )
                conf_val = float(item.get("confidence", 0.92))
                conf_lbl = item.get("confidence_level", "HIGH")
                t_id = item.get("task_id") or (candidate_tasks[idx-1]["task_id"] if idx-1 < len(candidate_tasks) else None)
                g_id = item.get("goal_id") or (candidate_tasks[idx-1]["goal_id"] if idx-1 < len(candidate_tasks) else None)

                persisted_items_data.append({
                    "task_id": t_id,
                    "goal_id": g_id,
                    "priority": prio_num,
                    "priority_label": prio_lbl,
                    "action": action_text,
                    "reason": reason_text,
                    "estimated_time": time_str,
                    "estimated_minutes": est_mins,
                    "evidence": ev_str,
                    "confidence": conf_val,
                    "confidence_level": conf_lbl,
                    "is_completed": False,
                })
                total_time_mins += est_mins
        else:
            # Deterministic fallback mapping
            for idx, c in enumerate(candidate_tasks, start=1):
                est_mins = c["estimated_duration_minutes"]
                time_str = f"{est_mins} minutes" if est_mins < 60 else f"{est_mins // 60}h {est_mins % 60}m"
                ev_str = c.get("evidence_text") or f"Grounded in goal '{c.get('goal_title')}' ({c.get('goal_importance')} importance)"

                persisted_items_data.append({
                    "task_id": c["task_id"],
                    "goal_id": c["goal_id"],
                    "priority": idx,
                    "priority_label": f"#{idx} - {c['priority']}",
                    "action": f"Execute {c['title']}: {c['description']}".strip(": "),
                    "reason": f"Rank #{idx}: Advances {c['goal_importance']} goal with {c['priority']} priority.",
                    "estimated_time": time_str,
                    "estimated_minutes": est_mins,
                    "evidence": ev_str,
                    "confidence": 0.95 if c.get("evidence_text") else 0.88,
                    "confidence_level": "HIGH",
                    "is_completed": False,
                })
                total_time_mins += est_mins

        if not plan_summary:
            plan_summary = (
                f"Action Plan for '{query}': {len(persisted_items_data)} tasks prioritized totaling "
                f"{total_time_mins} minutes within your {eff_available_minutes}m daily budget."
            )

        # 9. Persist Plan and Items to SQLite Relational Database
        plan_repo = ActionPlanRepository(db)
        persisted_plan = plan_repo.create_plan(
            user_id=user_id,
            query=query,
            summary=plan_summary,
            total_estimated_minutes=total_time_mins,
            available_minutes_constraint=eff_available_minutes,
            user_context_snapshot=merged_constraints,
            items_data=persisted_items_data,
            status="ACTIVE",
        )

        # 10. Record Activity Log
        ActivityLogRepository(db).log_activity(
            entity_type="ACTION_PLAN",
            action="GENERATED",
            entity_id=persisted_plan.id,
            user_id=user_id,
            details=f"Generated plan for '{query}' with {len(persisted_items_data)} items ({total_time_mins}m total).",
        )

        return persisted_plan

    def _calculate_task_score(
        self,
        task: Task,
        parent_goal: Optional[Goal],
        now: datetime,
        focus_areas: List[str],
        has_evidence: bool,
    ) -> float:
        """
        Computes a deterministic, explainable priority score.
        Score components:
        - Deadline Urgency (10 - 100)
        - Goal Importance (5 - 45)
        - Task Base Priority (5 - 40)
        - Document Evidence Grounding (+15)
        - Focus Area Alignment (+10)
        """
        score = 0.0

        # 1. Deadline Urgency
        if task.deadline:
            dl = task.deadline if task.deadline.tzinfo else task.deadline.replace(tzinfo=timezone.utc)
            delta = dl - now
            if delta < timedelta(0):  # Overdue
                score += 100.0
            elif delta <= timedelta(hours=24):  # Due today
                score += 90.0
            elif delta <= timedelta(hours=48):  # Due tomorrow
                score += 75.0
            elif delta <= timedelta(days=7):   # Due this week
                score += 50.0
            else:
                score += 25.0
        else:
            score += 10.0

        # 2. Goal Importance
        if parent_goal:
            imp = (parent_goal.importance or "MEDIUM").upper()
            if imp == "CRITICAL":
                score += 45.0
            elif imp == "HIGH":
                score += 30.0
            elif imp == "MEDIUM":
                score += 15.0
            else:
                score += 5.0
        else:
            score += 5.0

        # 3. Task Priority
        prio = (task.priority or "MEDIUM").upper()
        if prio == "URGENT":
            score += 40.0
        elif prio == "HIGH":
            score += 25.0
        elif prio == "MEDIUM":
            score += 15.0
        else:
            score += 5.0

        # 4. Document Evidence Grounding
        if has_evidence:
            score += 15.0

        # 5. Focus Areas
        if task.category and any(task.category.lower() == f.lower() for f in focus_areas):
            score += 10.0

        return score

action_planner = ActionPlanner()
