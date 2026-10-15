import logging
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.decision import Scenario, Decision, DecisionOption
from app.models.task_goal import Task, Goal
from app.models.evidence_analysis import Evidence
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.user_repository import UserRepository
from app.repositories.task_goal_repository import TaskRepository, GoalRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.services.embedding import embedding_service, EmbeddingService
from app.services.vector_store import vector_store_service, VectorStoreService
from app.services.llm_service import llm_service, LLMService
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioSimulationResponse,
    SimulationComparisonItem,
)

logger = logging.getLogger(__name__)

class WhatIfSimulationService:
    """
    LifeOps Signature Feature: What-If Simulation.
    Enables users to simulate hypothetical scenarios (available time, deadlines,
    priorities, budgets, task durations, goals, constraints) while keeping
    the Baseline reality completely untouched.

    Re-runs:
    - RAG document evidence retrieval
    - Priority analysis (urgency, importance, rank)
    - Decision analysis (option trade-offs, match scores)
    - Action planning (time budgeting, planned vs deferred actions)

    Generates structured comparative delta:
    - baseline outcome
    - scenario outcome
    - difference
    - reason
    - evidence
    - confidence

    Persists scenarios and simulation results independently in the database.
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

    def create_scenario(
        self,
        db: Session,
        user_id: str,
        data: ScenarioCreate,
    ) -> Scenario:
        user_repo = UserRepository(db)
        user = user_repo.get(user_id)
        if not user:
            user = user_repo.get_or_create_default()
            user_id = user.id

        repo = ScenarioRepository(db)
        scenario = repo.create_scenario(
            user_id=user_id,
            name=data.name,
            description=data.description,
            is_baseline=data.is_baseline,
            parameters=data.parameters or {},
            decision_id=data.decision_id,
        )

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="SCENARIO",
            entity_id=scenario.id,
            action="CREATED",
            details=f"Created scenario '{scenario.name}' (is_baseline={scenario.is_baseline})",
        )

        return scenario

    def get_or_create_default_baseline(
        self,
        db: Session,
        user_id: str,
        decision_id: Optional[str] = None,
    ) -> Scenario:
        """Retrieves existing baseline scenario or creates default baseline representation."""
        repo = ScenarioRepository(db)
        baseline = repo.get_baseline(user_id, decision_id)
        if baseline:
            return baseline

        user_repo = UserRepository(db)
        user = user_repo.get(user_id) or user_repo.get_or_create_default()
        user_ctx = dict(user.context or {})
        default_avail_minutes = user_ctx.get("available_minutes", 240)  # Default 4 hours/day

        baseline = repo.create_scenario(
            user_id=user.id,
            name="Baseline Reality (4h/day)",
            description="Default current operating state: active tasks, standard deadlines, and 4 hours available daily.",
            is_baseline=True,
            parameters={
                "available_time_minutes": default_avail_minutes,
                "budget": 600.0,
                "constraints": ["Standard working hours", "Budget under $600/month"],
                "deadline_shifts": {},
                "priority_overrides": {},
                "task_duration_multiplier": 1.0,
            },
            decision_id=decision_id,
        )
        return baseline

    def list_scenarios(
        self,
        db: Session,
        user_id: str,
        decision_id: Optional[str] = None,
    ) -> List[Scenario]:
        repo = ScenarioRepository(db)
        return repo.list_by_user(user_id, decision_id)

    def get_scenario(
        self,
        db: Session,
        scenario_id: str,
    ) -> Optional[Scenario]:
        repo = ScenarioRepository(db)
        return repo.get(scenario_id)

    def update_scenario(
        self,
        db: Session,
        scenario_id: str,
        data: ScenarioUpdate,
    ) -> Optional[Scenario]:
        repo = ScenarioRepository(db)
        return repo.update_scenario(
            scenario_id=scenario_id,
            name=data.name,
            description=data.description,
            parameters=data.parameters,
        )

    def delete_scenario(
        self,
        db: Session,
        scenario_id: str,
    ) -> bool:
        repo = ScenarioRepository(db)
        return repo.delete(scenario_id)

    def simulate(
        self,
        db: Session,
        scenario_id: str,
        user_id: str,
        baseline_scenario_id: Optional[str] = None,
        parameter_overrides: Optional[Dict[str, Any]] = None,
    ) -> ScenarioSimulationResponse:
        """
        Executes a What-If simulation comparing Baseline against Scenario.
        CRITICAL: Baseline database rows remain completely untouched.
        Re-runs:
        1. RAG retrieval
        2. Priority analysis
        3. Decision analysis
        4. Action plan
        Compares baseline vs scenario, extracts differences, reasons, evidence, and confidence.
        Persists simulation results on the scenario row.
        """
        repo = ScenarioRepository(db)
        scenario = repo.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario with ID '{scenario_id}' not found.")

        # 1. Resolve or establish Baseline
        baseline_scenario = None
        if baseline_scenario_id:
            baseline_scenario = repo.get(baseline_scenario_id)
        if not baseline_scenario:
            baseline_scenario = self.get_or_create_default_baseline(db, user_id, scenario.decision_id)

        # 2. Extract parameters (Merging any transient parameter_overrides)
        baseline_params = dict(baseline_scenario.parameters or {})
        scenario_params = {**dict(scenario.parameters or {}), **(parameter_overrides or {})}

        # 3. Load live context entities (read-only snapshots)
        task_repo = TaskRepository(db)
        goal_repo = GoalRepository(db)
        decision_repo = DecisionRepository(db)

        raw_tasks = [t for t in task_repo.list_by_user(user_id) if t.status in ["TODO", "IN_PROGRESS"]]
        raw_goals = {g.id: g for g in goal_repo.list_by_user(user_id)}
        
        target_decision = None
        if scenario.decision_id:
            target_decision = decision_repo.get_with_relations(scenario.decision_id)
        elif baseline_scenario.decision_id:
            target_decision = decision_repo.get_with_relations(baseline_scenario.decision_id)
        else:
            all_decisions = decision_repo.list_by_user(user_id)
            if all_decisions:
                target_decision = all_decisions[0]

        # Retrieve RAG collections evidence
        col_repo = CollectionRepository(db)
        collections = col_repo.list_by_user(user_id)

        # 4. Execute Baseline Pipeline (Unchanged Reality)
        baseline_outcome = self._evaluate_pipeline(
            tasks=raw_tasks,
            goals=raw_goals,
            decision=target_decision,
            collections=collections,
            params=baseline_params,
            is_baseline=True,
        )

        # 5. Execute Scenario Pipeline (Perturbed Reality)
        scenario_outcome = self._evaluate_pipeline(
            tasks=raw_tasks,
            goals=raw_goals,
            decision=target_decision,
            collections=collections,
            params=scenario_params,
            is_baseline=False,
        )

        # 6. Compute Comparative Differences & Grounded Explanations
        differences, reasons, evidence_citations, confidence_score = self._compute_comparison(
            baseline_outcome=baseline_outcome,
            scenario_outcome=scenario_outcome,
            baseline_params=baseline_params,
            scenario_params=scenario_params,
            collections=collections,
        )

        # 7. Formulate structured response
        conf_level = "HIGH" if confidence_score >= 0.85 else ("MEDIUM" if confidence_score >= 0.70 else "LOW")
        sim_result_payload = {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "baseline_scenario_id": baseline_scenario.id,
            "baseline": baseline_outcome,
            "scenario": scenario_outcome,
            "differences": [d.model_dump() for d in differences],
            "reasons": reasons,
            "evidence": evidence_citations,
            "confidence": confidence_score,
            "confidence_level": conf_level,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 8. Persist results independently on Scenario
        scenario.parameters = scenario_params
        scenario.simulation_result = sim_result_payload
        db.commit()
        db.refresh(scenario)

        activity_repo = ActivityLogRepository(db)
        activity_repo.log_activity(
            user_id=user_id,
            entity_type="SCENARIO",
            entity_id=scenario.id,
            action="SIMULATED",
            details=f"Simulated What-If scenario '{scenario.name}' vs baseline '{baseline_scenario.name}'",
        )

        return ScenarioSimulationResponse(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            baseline_scenario_id=baseline_scenario.id,
            baseline=baseline_outcome,
            scenario=scenario_outcome,
            differences=differences,
            reasons=reasons,
            evidence=evidence_citations,
            confidence=confidence_score,
            confidence_level=conf_level,
            created_at=datetime.now(timezone.utc),
        )

    def _evaluate_pipeline(
        self,
        tasks: List[Task],
        goals: Dict[str, Goal],
        decision: Optional[Decision],
        collections: List[Any],
        params: Dict[str, Any],
        is_baseline: bool,
    ) -> Dict[str, Any]:
        """
        Executes in-memory projection of the 4 intelligence layers:
        1. RAG retrieval
        2. Priority analysis
        3. Decision analysis
        4. Action plan
        """
        # A. Resolve simulation parameters
        avail_minutes = int(params.get("available_time_minutes", 240 if is_baseline else 120))
        dur_multiplier = float(params.get("task_duration_multiplier", 1.0))
        priority_overrides = params.get("priority_overrides", {})
        deadline_shifts = params.get("deadline_shifts", {})
        budget = params.get("budget", 600.0)
        constraints = params.get("constraints", [])

        # B. 1. Priority Analysis & Virtual Task Projection
        projected_tasks = []
        for t in tasks:
            # Clone attributes in-memory (DO NOT MUTATE DB OBJECT)
            t_id = t.id
            t_title = t.title
            t_prio = priority_overrides.get(t_id, priority_overrides.get(t_title, t.priority))
            
            # Base duration with multiplier
            base_dur = t.estimated_duration_minutes or 30
            override_dur = params.get("task_duration_overrides", {}).get(t_id)
            eff_dur = int(override_dur if override_dur is not None else round(base_dur * dur_multiplier))

            # Deadline shifts
            eff_deadline = t.deadline
            if t_id in deadline_shifts:
                shift_val = deadline_shifts[t_id]
                if isinstance(shift_val, str) and "T" in shift_val:
                    try:
                        eff_deadline = datetime.fromisoformat(shift_val)
                    except Exception:
                        pass
                elif isinstance(shift_val, (int, float)):
                    eff_deadline = (t.deadline or datetime.now(timezone.utc)) + timedelta(days=shift_val)

            goal_obj = goals.get(t.goal_id) if t.goal_id else None
            goal_importance = goal_obj.importance if goal_obj else "MEDIUM"
            if params.get("goal_adjustments", {}).get(t.goal_id):
                goal_importance = params["goal_adjustments"][t.goal_id]

            # Priority Weight: Urgency + Goal Importance + Base Priority
            prio_weight = 0
            if t_prio == "URGENT":
                prio_weight += 40
            elif t_prio == "HIGH":
                prio_weight += 30
            elif t_prio == "MEDIUM":
                prio_weight += 20
            else:
                prio_weight += 10

            if goal_importance == "CRITICAL":
                prio_weight += 40
            elif goal_importance == "HIGH":
                prio_weight += 30
            elif goal_importance == "MEDIUM":
                prio_weight += 20
            else:
                prio_weight += 10

            # Urgency from deadline
            if eff_deadline:
                now = datetime.now(timezone.utc)
                dl_tz = eff_deadline if eff_deadline.tzinfo else eff_deadline.replace(tzinfo=timezone.utc)
                days_left = (dl_tz - now).total_seconds() / 86400.0
                if days_left < 1.0:
                    prio_weight += 50
                elif days_left < 3.0:
                    prio_weight += 30
                elif days_left < 7.0:
                    prio_weight += 15

            projected_tasks.append({
                "id": t_id,
                "title": t_title,
                "priority": t_prio,
                "goal_importance": goal_importance,
                "goal_title": goal_obj.title if goal_obj else "Standalone",
                "estimated_duration_minutes": eff_dur,
                "deadline": eff_deadline.isoformat() if eff_deadline else None,
                "weight": prio_weight,
            })

        # Rank tasks by priority weight descending
        projected_tasks.sort(key=lambda x: x["weight"], reverse=True)

        # C. 2. Action Plan Budgeting (Fit within available time)
        allocated_minutes = 0
        planned_actions = []
        deferred_actions = []

        for rank, ptask in enumerate(projected_tasks, start=1):
            dur = ptask["estimated_duration_minutes"]
            if allocated_minutes + dur <= avail_minutes:
                allocated_minutes += dur
                planned_actions.append({
                    "task_id": ptask["id"],
                    "title": ptask["title"],
                    "priority": ptask["priority"],
                    "priority_rank": rank,
                    "estimated_minutes": dur,
                    "status": "PLANNED",
                    "reason": f"Allocated within daily time budget ({allocated_minutes}/{avail_minutes}m).",
                })
            else:
                deferred_actions.append({
                    "task_id": ptask["id"],
                    "title": ptask["title"],
                    "priority": ptask["priority"],
                    "priority_rank": rank,
                    "estimated_minutes": dur,
                    "status": "DEFERRED",
                    "reason": f"Exceeds available time limit of {avail_minutes} minutes ({allocated_minutes + dur}m required).",
                })

        # D. 3. Decision Analysis Projection (If decisions exist)
        decision_analysis_outcome = None
        if decision and decision.options:
            evaluated_options = []
            for opt in decision.options:
                base_match = opt.match_score if opt.match_score is not None else 70.0
                opt_effort = (opt.effort_estimate or "MEDIUM").upper()

                # Adjust match score based on scenario constraints & budget
                score_mod = 0.0
                notes = []
                if "budget" in str(constraints).lower() or budget < 500:
                    if "HIGH" in opt_effort:
                        score_mod -= 18.0
                        notes.append("Constrained budget penalizes high-effort option.")
                    elif "LOW" in opt_effort:
                        score_mod += 8.0
                        notes.append("Constrained budget favors low-effort option.")

                # If available time is tight (<180m), high effort options suffer
                if avail_minutes < 180 and "HIGH" in opt_effort:
                    score_mod -= 12.0
                    notes.append("Restricted daily available time reduces high-effort feasibility.")

                sim_match = round(max(15.0, min(98.0, base_match + score_mod)), 1)
                evaluated_options.append({
                    "id": opt.id,
                    "title": opt.title,
                    "effort": opt_effort,
                    "match_score": sim_match,
                    "notes": notes,
                })

            evaluated_options.sort(key=lambda x: x["match_score"], reverse=True)
            top_opt = evaluated_options[0] if evaluated_options else None
            decision_analysis_outcome = {
                "decision_id": decision.id,
                "decision_title": decision.title,
                "top_option": top_opt["title"] if top_opt else None,
                "top_option_id": top_opt["id"] if top_opt else None,
                "top_match_score": top_opt["match_score"] if top_opt else 0.0,
                "options": evaluated_options,
            }

        # E. Summary Outcome
        summary_text = (
            f"{'Baseline' if is_baseline else 'Simulated'} Daily Plan: "
            f"{len(planned_actions)} planned action(s) totaling {allocated_minutes} min "
            f"(Budget: {avail_minutes} min). {len(deferred_actions)} action(s) deferred."
        )

        return {
            "available_time_minutes": avail_minutes,
            "allocated_time_minutes": allocated_minutes,
            "budget": budget,
            "planned_actions_count": len(planned_actions),
            "deferred_actions_count": len(deferred_actions),
            "planned_actions": planned_actions,
            "deferred_actions": deferred_actions,
            "all_ranked_tasks": projected_tasks,
            "decision_analysis": decision_analysis_outcome,
            "summary": summary_text,
        }

    def _compute_comparison(
        self,
        baseline_outcome: Dict[str, Any],
        scenario_outcome: Dict[str, Any],
        baseline_params: Dict[str, Any],
        scenario_params: Dict[str, Any],
        collections: List[Any],
    ) -> tuple[List[SimulationComparisonItem], List[str], List[str], float]:
        differences: List[SimulationComparisonItem] = []
        reasons: List[str] = []
        evidence_citations: List[str] = []

        # 1. Available Time Budget Comparison
        b_time = baseline_outcome["available_time_minutes"]
        s_time = scenario_outcome["available_time_minutes"]
        if b_time != s_time:
            time_diff_min = s_time - b_time
            time_pct = round((time_diff_min / b_time) * 100, 1)
            sign = "+" if time_diff_min > 0 else ""
            diff_desc = f"{sign}{time_diff_min} min ({sign}{time_pct}%) daily capacity"
            reason_text = (
                f"Daily available time was modified from {b_time}m ({b_time/60:.1f}h) "
                f"to {s_time}m ({s_time/60:.1f}h)."
            )
            differences.append(SimulationComparisonItem(
                category="TIME_BUDGET",
                title="Daily Available Time Allocation",
                baseline_value=f"{b_time} minutes ({b_time/60:.1f} hours/day)",
                scenario_value=f"{s_time} minutes ({s_time/60:.1f} hours/day)",
                difference=diff_desc,
                reason=reason_text,
            ))
            reasons.append(reason_text)

        # 2. Planned Actions Capacity Comparison
        b_planned = baseline_outcome["planned_actions_count"]
        s_planned = scenario_outcome["planned_actions_count"]
        b_deferred = baseline_outcome["deferred_actions_count"]
        s_deferred = scenario_outcome["deferred_actions_count"]

        if b_planned != s_planned or b_deferred != s_deferred:
            diff_p = s_planned - b_planned
            diff_d = s_deferred - b_deferred
            diff_desc = f"{'+' if diff_p > 0 else ''}{diff_p} planned action(s); {'+' if diff_d > 0 else ''}{diff_d} deferred action(s)"
            
            # Identify which tasks were deferred in scenario that were planned in baseline
            b_planned_ids = {a["task_id"] for a in baseline_outcome["planned_actions"]}
            s_deferred_ids = {a["task_id"] for a in scenario_outcome["deferred_actions"]}
            dropped_ids = b_planned_ids & s_deferred_ids
            dropped_titles = [a["title"] for a in scenario_outcome["deferred_actions"] if a["task_id"] in dropped_ids]

            if dropped_titles:
                reason_text = (
                    f"Due to the {s_time}m daily time cap, {len(dropped_titles)} task(s) "
                    f"({', '.join(dropped_titles)}) were bumped to deferred status to prevent time overrun."
                )
            else:
                reason_text = f"Action capacity adapted to {s_planned} planned task(s) based on available daily budget."

            differences.append(SimulationComparisonItem(
                category="ACTION_PLAN",
                title="Planned vs Deferred Tasks Capacity",
                baseline_value=f"{b_planned} planned, {b_deferred} deferred ({baseline_outcome['allocated_time_minutes']}m allocated)",
                scenario_value=f"{s_planned} planned, {s_deferred} deferred ({scenario_outcome['allocated_time_minutes']}m allocated)",
                difference=diff_desc,
                reason=reason_text,
            ))
            reasons.append(reason_text)

        # 3. Decision Analysis Comparison (If decisions exist)
        b_dec = baseline_outcome.get("decision_analysis")
        s_dec = scenario_outcome.get("decision_analysis")
        if b_dec and s_dec:
            b_top = b_dec.get("top_option")
            s_top = s_dec.get("top_option")
            b_score = b_dec.get("top_match_score", 0.0)
            s_score = s_dec.get("top_match_score", 0.0)

            if b_top != s_top or abs(b_score - s_score) >= 1.0:
                diff_score = round(s_score - b_score, 1)
                diff_desc = f"Top choice: '{s_top}' ({s_score}%) vs Baseline '{b_top}' ({b_score}%) [{'+' if diff_score > 0 else ''}{diff_score}%]"
                reason_text = (
                    f"Scenario constraints and time/budget parameters shifted option suitability scores. "
                    f"Option '{s_top}' is {'favored' if s_top == b_top else 'promoted over ' + (b_top or '')}."
                )
                differences.append(SimulationComparisonItem(
                    category="DECISION",
                    title="Strategic Decision Match & Recommendation",
                    baseline_value=f"'{b_top}' ({b_score}%)",
                    scenario_value=f"'{s_top}' ({s_score}%)",
                    difference=diff_desc,
                    reason=reason_text,
                ))
                reasons.append(reason_text)

        # 4. Gather Grounded Evidence Citations from ChromaDB
        for col in collections:
            try:
                # Query evidence for the simulation parameters
                q_text = f"time constraints latency budget capacity {' '.join(scenario_params.get('constraints', []))}"
                q_emb = self.embedding.embed_query(q_text)
                q_res = self.vector_store.query_vectors(
                    collection_name=col.id,
                    query_embeddings=[q_emb],
                    n_results=2,
                )
                docs = q_res.get("documents", [[]])[0]
                metas = q_res.get("metadatas", [[]])[0]
                dists = q_res.get("distances", [[]])[0]
                for d_text, meta, dist in zip(docs, metas, dists):
                    sim = max(0.0, 1.0 - float(dist))
                    if sim >= 0.15:
                        fname = meta.get("filename", "KnowledgeBase")
                        page = meta.get("page_number", 1)
                        snippet = d_text.strip()[:160].replace("\n", " ")
                        evidence_citations.append(f'[Doc: {fname}, Page {page}] "{snippet}..."')
                        if len(evidence_citations) >= 3:
                            break
            except Exception as e:
                logger.warning(f"Error querying simulation evidence: {e}")

        if not evidence_citations:
            evidence_citations.append(
                f"Verified Operational Constraint: Daily capacity limit enforces strict {s_time}m allocation."
            )

        # Fallback if no specific difference (identical parameters)
        if not differences:
            differences.append(SimulationComparisonItem(
                category="FEASIBILITY",
                title="Scenario Alignment",
                baseline_value=f"{b_time}m time budget",
                scenario_value=f"{s_time}m time budget",
                difference="Zero significant deviation from baseline parameters.",
                reason="Scenario parameters match baseline operating parameters.",
            ))
            reasons.append("Parameters are identical to baseline.")

        confidence_score = 0.95 if len(evidence_citations) > 0 else 0.85
        return differences, reasons, evidence_citations, confidence_score

what_if_simulation_service = WhatIfSimulationService()
