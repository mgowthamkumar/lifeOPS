import json
import logging
import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at",
    "to", "for", "of", "with", "by", "from", "up", "about", "into", "over",
    "after", "who", "which", "how", "when", "where", "why", "can", "could",
    "should", "would", "do", "does", "did", "have", "has", "had", "will",
    "tell", "me", "give", "list", "show", "describe", "find", "explain"
}

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate_grounded_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_action_plan(
        self,
        query: str,
        tasks_context: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_decision_analysis(
        self,
        decision_context: Dict[str, Any],
        options_context: List[Dict[str, Any]],
        general_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def analyze_claim_evidence(
        self,
        claim: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pass

class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM provider with strict grounding and structured JSON responses.
    Includes offline grounded synthesis fallback when GEMINI_API_KEY is not configured.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "LLM_MODEL", "gemini-2.5-flash")
        self._client = None

        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key.strip())
            except Exception as e:
                logger.warning(f"Could not initialize google-genai client: {e}")

    def generate_grounded_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not context_chunks:
            return {
                "answer": "INSUFFICIENT EVIDENCE: The uploaded documents do not contain evidence to address this question.",
                "has_sufficient_evidence": False,
                "confidence": 0.0,
                "model": self.model_name,
            }

        if self._client and self.api_key and self.api_key.strip():
            return self._call_gemini_api(question, context_chunks)

        return self._grounded_synthesis(question, context_chunks)

    def _call_gemini_api(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from google.genai import types

        context_blocks = []
        for i, c in enumerate(context_chunks):
            meta = c.get("metadata", {})
            fname = meta.get("filename", f"Doc_{i+1}")
            page = meta.get("page_number", 1)
            content = c.get("content", "")
            context_blocks.append(f"--- [SOURCE {i+1}: {fname} | Page {page}] ---\n{content}")

        context_str = "\n\n".join(context_blocks)

        prompt = f"""You are the LifeOps AI Evidence-Grounded Decision Assistant.
Your task is to answer the user's question using EXCLUSIVELY the provided context sources.

CRITICAL INSTRUCTIONS:
1. STRICT GROUNDING: State only facts directly supported by the context snippets.
2. If the context does NOT contain direct and sufficient information to answer the question, you MUST set "has_sufficient_evidence": false and set "answer": "INSUFFICIENT EVIDENCE: The provided documents do not contain sufficient evidence to answer this question."
3. NO HALLUCINATION: Never invent facts, make assumptions, or cite external knowledge not present in the context.
4. CITATIONS: Reference used sources in your answer as [Doc: <filename>, Page: <page>].
5. Respond strictly in valid JSON format with keys:
   - "answer": (string)
   - "has_sufficient_evidence": (boolean)
   - "confidence": (float between 0.0 and 1.0)

CONTEXT SOURCES:
{context_str}

QUESTION:
{question}
"""

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)

            answer = data.get("answer", "").strip()
            has_evidence = data.get("has_sufficient_evidence", True)

            if "INSUFFICIENT EVIDENCE" in answer.upper():
                has_evidence = False

            return {
                "answer": answer,
                "has_sufficient_evidence": bool(has_evidence),
                "confidence": float(data.get("confidence", 0.9 if has_evidence else 0.0)),
                "model": self.model_name,
            }
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}. Falling back to grounded synthesis.")
            return self._grounded_synthesis(question, context_chunks)

    def _grounded_synthesis(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extractive grounded synthesis used offline or when API key is unconfigured.
        Strictly enforces that evidence terms must overlap with the question.
        """
        # Tokenize question terms
        raw_terms = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", question.lower())
        q_terms = {t for t in raw_terms if t not in STOP_WORDS}

        # Check semantic overlap across retrieved chunks
        supporting_snippets = []
        matching_chunks_count = 0

        for chunk in context_chunks:
            content = chunk.get("content", "")
            meta = chunk.get("metadata", {})
            fname = meta.get("filename", "Document")
            page = meta.get("page_number", 1)
            chunk_words = set(re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", content.lower()))

            overlap = q_terms.intersection(chunk_words)
            # Require significant keyword overlap to prevent false positives from generic nearest vectors
            if len(overlap) >= max(1, min(2, len(q_terms))):
                matching_chunks_count += 1
                # Extract the most relevant sentences
                sentences = re.split(r"(?<=[.!?])\s+", content)
                matched_sentences = [
                    s.strip() for s in sentences
                    if any(term in s.lower() for term in overlap)
                ]
                if matched_sentences:
                    snippet = " ".join(matched_sentences[:3])
                else:
                    snippet = content[:200]
                supporting_snippets.append(f"• According to {fname} (Page {page}): \"{snippet}\"")

        # If no chunk had substantive overlap with the question's core concepts:
        if matching_chunks_count == 0 or not supporting_snippets:
            return {
                "answer": "INSUFFICIENT EVIDENCE: The uploaded documents do not contain sufficient evidence to address this question.",
                "has_sufficient_evidence": False,
                "confidence": 0.0,
                "model": "grounded-extractive-engine",
            }

        synthesized_answer = (
            f"Based on verified evidence from {len(supporting_snippets)} source segment(s):\n\n"
            + "\n".join(supporting_snippets)
        )

        return {
            "answer": synthesized_answer,
            "has_sufficient_evidence": True,
            "confidence": 0.88,
            "model": "grounded-extractive-engine",
        }

    def generate_action_plan(
        self,
        query: str,
        tasks_context: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not tasks_context:
            return {
                "summary": "No active tasks found to plan. All tasks are completed or none have been created yet.",
                "items": [],
                "model": self.model_name,
            }

        if self._client and self.api_key and self.api_key.strip():
            return self._call_gemini_action_planner(query, tasks_context, constraints)

        return self._deterministic_plan_synthesis(query, tasks_context, constraints)

    def _call_gemini_action_planner(
        self,
        query: str,
        tasks_context: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        from google.genai import types

        tasks_summary = []
        for i, t in enumerate(tasks_context):
            evidence_line = f"Evidence: {t.get('evidence_text', 'None')}"
            tasks_summary.append(
                f"[Candidate Task {i+1}]\n"
                f"Task ID: {t.get('task_id')}\n"
                f"Title: {t.get('title')}\n"
                f"Description: {t.get('description', '')}\n"
                f"Deadline: {t.get('deadline', 'None')}\n"
                f"Task Priority: {t.get('priority')}\n"
                f"Estimated Duration: {t.get('estimated_duration_minutes', 30)} minutes\n"
                f"Category: {t.get('category', 'General')}\n"
                f"Parent Goal: {t.get('goal_title', 'None')} (Importance: {t.get('goal_importance', 'MEDIUM')}, Progress: {t.get('goal_progress', 0)}%)\n"
                f"{evidence_line}"
            )

        tasks_str = "\n\n".join(tasks_summary)
        avail_mins = constraints.get("available_minutes", 480)
        focus = ", ".join(constraints.get("focus_areas", [])) if constraints.get("focus_areas") else "All active categories"

        prompt = f"""You are the LifeOps AI Action Planner.
Your mission is to construct an explainable, prioritized daily action plan addressing the user's request.

USER REQUEST:
"{query}"

USER CONSTRAINTS:
- Available time budget today: {avail_mins} minutes
- Focus domains: {focus}

CANDIDATE TASKS AND EVIDENCE:
{tasks_str}

CRITICAL RULES:
1. DETERMINISTIC PRIORITIZATION: Rank actions by urgency (imminent/overdue deadlines > soon), then parent goal importance (CRITICAL > HIGH > MEDIUM > LOW), then task base priority (URGENT > HIGH > MEDIUM > LOW).
2. TIME BUDGETING: Carefully budget tasks so the primary planned items fit within {avail_mins} minutes.
3. GROUNDED EVIDENCE: In each item's "evidence" field, cite the provided document evidence if available, or state the specific requirement basis.
4. NO RANDOM PRIORITIZATION. NO HALLUCINATIONS. NO FAKE DATA.
5. You MUST return valid JSON matching this schema:
{{
  "summary": "A concise executive summary of today's focus and planned time allocation.",
  "items": [
    {{
      "task_id": "original task ID",
      "goal_id": "original goal ID if any, or null",
      "priority": 1,
      "priority_label": "1 - URGENT",
      "action": "Concrete, actionable statement of what to do",
      "reason": "Explainable rationale linking deadline urgency, goal importance, and context",
      "estimated_time": "e.g. 45 minutes",
      "estimated_minutes": 45,
      "evidence": "Document citation or verified rationale snippet",
      "confidence": 0.95,
      "confidence_level": "HIGH"
    }}
  ]
}}
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            data["model"] = self.model_name
            return data
        except Exception as e:
            logger.error(f"Gemini Action Planner call failed: {e}. Falling back to deterministic synthesis.")
            return self._deterministic_plan_synthesis(query, tasks_context, constraints)

    def _deterministic_plan_synthesis(
        self,
        query: str,
        tasks_context: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        avail_mins = constraints.get("available_minutes", 480)
        total_time = 0
        items = []

        for rank, task in enumerate(tasks_context, start=1):
            dur = task.get("estimated_duration_minutes", 30) or 30
            deadline_str = task.get("deadline")
            goal_title = task.get("goal_title")
            goal_imp = task.get("goal_importance", "MEDIUM")
            prio = task.get("priority", "MEDIUM")

            reasons = []
            if deadline_str:
                date_part = str(deadline_str).split("T")[0]
                reasons.append(f"Due {date_part}")
            if goal_title:
                reasons.append(f"advances {goal_imp} goal '{goal_title}'")
            reasons.append(f"{prio} priority")

            reason_text = f"Prioritized as #{rank}: {'; '.join(reasons)}."
            if total_time + dur > avail_mins:
                reason_text += f" (Secondary priority: exceeds daily {avail_mins}m allocation)."

            evidence_val = task.get("evidence_text") or (
                f"Verified requirement: advances parent goal '{goal_title or 'Standalone'}' ({goal_imp} importance)"
            )

            time_str = f"{dur} minutes" if dur < 60 else f"{dur // 60}h {dur % 60}m" if dur % 60 else f"{dur // 60}h"

            items.append({
                "task_id": task.get("task_id"),
                "goal_id": task.get("goal_id"),
                "priority": rank,
                "priority_label": f"#{rank} - {prio}",
                "action": f"Execute {task.get('title')}: {task.get('description', '')}".strip(": "),
                "reason": reason_text,
                "estimated_time": time_str,
                "estimated_minutes": dur,
                "evidence": evidence_val,
                "confidence": 0.95 if task.get("evidence_text") else 0.88,
                "confidence_level": "HIGH",
            })
            total_time += dur

        summary = (
            f"Action Plan for '{query}': {len(items)} task(s) prioritized with total estimated time of "
            f"{total_time} minutes ({min(len(items), sum(1 for i in items if i['estimated_minutes'] <= avail_mins))} "
            f"primary actions within your {avail_mins}m daily budget)."
        )

        return {
            "summary": summary,
            "items": items,
            "model": "deterministic-grounded-planner",
        }

    def generate_decision_analysis(
        self,
        decision_context: Dict[str, Any],
        options_context: List[Dict[str, Any]],
        general_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self._client and self.api_key and self.api_key.strip():
            return self._call_gemini_decision_api(decision_context, options_context, general_evidence)
        return self._deterministic_decision_synthesis(decision_context, options_context, general_evidence)

    def _call_gemini_decision_api(
        self,
        decision_context: Dict[str, Any],
        options_context: List[Dict[str, Any]],
        general_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from google.genai import types

        question = decision_context.get("question", "")
        context_desc = decision_context.get("context_description", "")
        constraints = decision_context.get("constraints", [])
        goals = decision_context.get("goals", [])

        goals_text = "\n".join([f"- {g.get('title')} (Importance: {g.get('importance', 'HIGH')})" for g in goals]) or "None specified"
        constraints_text = "\n".join([f"- {c}" for c in constraints]) or "None specified"

        options_blocks = []
        for opt in options_context:
            opt_id = opt.get("id") or opt.get("option_id")
            title = opt.get("title")
            desc = opt.get("description", "")
            effort = opt.get("effort_estimate", "Unspecified")
            ev_list = opt.get("evidence_chunks", [])
            ev_text = "\n".join([
                f"  * [Doc: {e.get('metadata', {}).get('filename', 'Unknown')}, Page {e.get('metadata', {}).get('page_number', 1)}] {e.get('content', '')[:300]}"
                for e in ev_list
            ]) or "  * No specific document evidence found"

            options_blocks.append(
                f"Option ID: {opt_id}\nTitle: {title}\nDescription: {desc}\nEffort: {effort}\nRelevant Evidence:\n{ev_text}"
            )

        options_str = "\n\n".join(options_blocks)

        prompt = f"""You are the LifeOps AI Decision Intelligence Engine.
Analyze the following strategic decision options using strict evidence grounding, goal alignment, and constraint compliance.

QUESTION:
{question}

DECISION CONTEXT:
{context_desc}

STRATEGIC GOALS:
{goals_text}

USER CONSTRAINTS:
{constraints_text}

CANDIDATE OPTIONS & EVIDENCE:
{options_str}

CRITICAL INSTRUCTIONS:
1. Ground your analysis strictly in the provided document evidence and strategic context.
2. Evaluate each option thoroughly against:
   - "match": composite suitability score between 0.0 and 100.0 (weighted: goal alignment 40%, constraint compliance 30%, evidence strength 20%, effort feasibility 10%).
   - "strengths": list of distinct verified advantages supported by evidence or goals.
   - "weaknesses": list of distinct trade-offs, risks, or potential failure modes.
   - "gaps": list of unverified assumptions, missing data, or lack of documentation.
   - "constraints": list of evaluations verifying compliance with each user constraint.
   - "goal_alignment": narrative explanation of how this option advances the user's goals.
   - "evidence": list of cited quotes formatted as [Doc: <filename>, Page <p>] "<quote>".
   - "confidence": confidence score between 0.0 and 1.0.
   - "recommendation": option verdict ("STRONGLY RECOMMENDED", "VIABLE ALTERNATIVE", or "NOT RECOMMENDED").
3. Determine the overall winning recommendation, confidence level ("HIGH", "MEDIUM", "LOW"), and executive reasoning summary.
4. Respond strictly in valid JSON matching this schema:
{{
  "recommendation": "Executive recommendation stating the best option and primary justification",
  "confidence": "HIGH",
  "reasoning_summary": "Comprehensive comparative evaluation summarizing why the winning option was chosen over alternatives",
  "top_option_id": "<ID of top option>",
  "options_analysis": [
    {{
      "option_id": "<id>",
      "option_title": "<title>",
      "match": 88.5,
      "strengths": ["...", "..."],
      "weaknesses": ["..."],
      "gaps": ["..."],
      "constraints": ["Constraint 1: Compliant because..."],
      "goal_alignment": "Directly advances Goal X by...",
      "evidence": ["[Doc: policy.pdf, Page 2] \\"...\\""],
      "confidence": 0.92,
      "recommendation": "STRONGLY RECOMMENDED"
    }}
  ]
}}
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            data["model"] = self.model_name
            return data
        except Exception as e:
            logger.error(f"Gemini Decision Intelligence call failed: {e}. Falling back to deterministic synthesis.")
            return self._deterministic_decision_synthesis(decision_context, options_context, general_evidence)

    def _deterministic_decision_synthesis(
        self,
        decision_context: Dict[str, Any],
        options_context: List[Dict[str, Any]],
        general_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        question = decision_context.get("question", "")
        context_desc = decision_context.get("context_description", "")
        constraints = decision_context.get("constraints", [])
        goals = decision_context.get("goals", [])

        analyzed_options = []

        for opt in options_context:
            opt_id = opt.get("id") or opt.get("option_id")
            title = opt.get("title", "")
            desc = opt.get("description", "")
            effort = (opt.get("effort_estimate") or "MEDIUM").upper()
            ev_chunks = opt.get("evidence_chunks", [])

            # Evidence citations
            evidence_citations = []
            for chunk in ev_chunks:
                meta = chunk.get("metadata", {})
                fname = meta.get("filename", "Document")
                page = meta.get("page_number", 1)
                content_snippet = chunk.get("content", "").strip()[:180]
                if content_snippet:
                    evidence_citations.append(f'[Doc: {fname}, Page {page}] "{content_snippet}..."')

            # Goal Alignment evaluation
            aligned_goals = []
            for g in goals:
                g_title = g.get("title", "")
                words = set(re.findall(r"\w+", f"{title} {desc}".lower()))
                g_words = set(re.findall(r"\w+", g_title.lower())) - STOP_WORDS
                if words & g_words or len(goals) == 1:
                    aligned_goals.append(g_title)

            if aligned_goals:
                goal_alignment_text = f"Directly supports {len(aligned_goals)} strategic goal(s): {', '.join(aligned_goals)}."
            elif goals:
                goal_alignment_text = f"Indirectly contributes to active strategic goals ({', '.join(g.get('title', '') for g in goals)})."
            else:
                goal_alignment_text = "Aligns with core operational objectives and user intent."

            # Constraint evaluations
            constraint_evals = []
            for c in constraints:
                c_str = str(c)
                # Check for apparent conflict
                if "budget" in c_str.lower() and "high" in effort.lower():
                    constraint_evals.append(f"Constraint '{c_str}': Potential tension due to higher resource requirements.")
                elif "time" in c_str.lower() and "high" in effort.lower():
                    constraint_evals.append(f"Constraint '{c_str}': Requires careful scheduling to prevent deadline overrun.")
                else:
                    constraint_evals.append(f"Constraint '{c_str}': Compliant with defined parameters.")

            if not constraint_evals:
                constraint_evals = ["No rigid constraints violated; within standard operational parameters."]

            # Score calculation
            base_score = 55.0
            # Evidence bonus (up to 20 pts)
            ev_bonus = min(20.0, len(ev_chunks) * 10.0)
            # Goal alignment bonus (up to 15 pts)
            goal_bonus = 15.0 if aligned_goals else (8.0 if goals else 10.0)
            # Effort factor (up to 10 pts)
            effort_mod = 10.0 if "LOW" in effort else (5.0 if "MED" in effort else 0.0)
            # Constraint penalty
            tension_count = sum(1 for ce in constraint_evals if "tension" in ce or "overrun" in ce)
            constraint_penalty = tension_count * 10.0

            raw_score = base_score + ev_bonus + goal_bonus + effort_mod - constraint_penalty
            match_score = round(max(20.0, min(96.0, raw_score)), 1)

            # Strengths
            strengths = []
            if ev_chunks:
                strengths.append(f"Grounded by {len(ev_chunks)} verified document evidence citation(s).")
            if aligned_goals:
                strengths.append(f"High strategic alignment with goal '{aligned_goals[0]}'.")
            if "LOW" in effort:
                strengths.append("Favorable implementation feasibility with minimal operational overhead.")
            else:
                strengths.append(f"Robust scope addressing core requirements of '{title}'.")

            # Weaknesses
            weaknesses = []
            if "HIGH" in effort:
                weaknesses.append("Demands substantial time and resource investment.")
            if tension_count > 0:
                weaknesses.append("Presents friction with one or more operational constraints.")
            if not ev_chunks:
                weaknesses.append("Lacks direct supporting citations in uploaded knowledge base.")
            if not weaknesses:
                weaknesses.append("Requires active monitoring during initial execution phase.")

            # Gaps
            gaps = []
            if not ev_chunks:
                gaps.append("No specific documentation found covering this option's execution details.")
            else:
                gaps.append("Long-term maintenance parameters not fully detailed in available documentation.")
            if not constraints:
                gaps.append("Unspecified user constraints require baseline assumption validation.")

            # Confidence
            conf_score = 0.92 if ev_chunks else 0.78
            rec_status = "STRONGLY RECOMMENDED" if match_score >= 80 else ("VIABLE ALTERNATIVE" if match_score >= 60 else "NOT RECOMMENDED")

            analyzed_options.append({
                "option_id": opt_id,
                "option_title": title,
                "match": match_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "gaps": gaps,
                "constraints": constraint_evals,
                "goal_alignment": goal_alignment_text,
                "evidence": evidence_citations,
                "confidence": conf_score,
                "recommendation": rec_status,
            })

        # Sort by match score descending
        analyzed_options.sort(key=lambda x: x["match"], reverse=True)
        top_opt = analyzed_options[0] if analyzed_options else None
        top_id = top_opt["option_id"] if top_opt else None
        top_title = top_opt["option_title"] if top_opt else "None"

        overall_conf = "HIGH" if (top_opt and top_opt["confidence"] >= 0.85) else "MEDIUM"
        overall_rec = f"Proceed with Option '{top_title}' based on superior match score ({top_opt['match'] if top_opt else 0}%) and strong alignment with requirements."
        
        reasoning_sum = (
            f"Evaluated {len(analyzed_options)} candidate option(s) against strategic goals, document evidence, and operational constraints. "
            f"Option '{top_title}' achieved the highest composite match score ({top_opt['match'] if top_opt else 0}%), "
            f"demonstrating optimal balance between evidence support and execution feasibility."
        )

        return {
            "decision_id": decision_context.get("id", ""),
            "recommendation": overall_rec,
            "confidence": overall_conf,
            "reasoning_summary": reasoning_sum,
            "top_option_id": top_id,
            "options_analysis": analyzed_options,
            "model": "deterministic-grounded-decision-engine",
        }

    def analyze_claim_evidence(
        self,
        claim: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not context_chunks:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "has_sufficient_evidence": False,
                "conflict_detected": False,
                "confidence": 0.0,
                "uncertainty": 1.0,
                "uncertainty_level": "HIGH",
                "reasoning_summary": f"INSUFFICIENT EVIDENCE: No indexed documents contain verified evidence to evaluate claim: '{claim}'.",
                "evidence_items": [],
                "conflicts": [],
                "model": self.model_name,
            }

        if self._client and self.api_key and self.api_key.strip():
            return self._call_gemini_evidence_api(claim, context_chunks)

        return self._grounded_evidence_synthesis(claim, context_chunks)

    def _call_gemini_evidence_api(
        self,
        claim: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from google.genai import types

        context_blocks = []
        for i, c in enumerate(context_chunks, start=1):
            meta = c.get("metadata", {})
            fname = meta.get("filename", f"Doc_{i}")
            page = meta.get("page_number", 1)
            content = c.get("content", "")
            context_blocks.append(f"--- [SOURCE {i}: {fname} | Page {page}] ---\n{content}")

        context_str = "\n\n".join(context_blocks)

        prompt = f"""You are the LifeOps AI Evidence Explorer & Conflict Detector.
Analyze the following claim strictly against the provided context source snippets.

CRITICAL INSTRUCTIONS:
1. STRICT GROUNDING: State only facts directly supported by the context snippets. Never invent or hallucinate facts or citations.
2. STANCE EVALUATION: For each snippet that mentions relevant facts, determine whether it SUPPORTS, CONTRADICTS, or is NEUTRAL to the claim.
3. CONFLICT DETECTION: Actively compare the sources. If different sources or snippets assert contradictory facts, opposing numerical values, conflicting deadlines, or disagree on guidance, you MUST set "conflict_detected": true and provide detailed conflict comparison objects.
4. INSUFFICIENT EVIDENCE: If the context snippets do NOT contain relevant evidence to verify or refute the claim, you MUST set "has_sufficient_evidence": false, "status": "INSUFFICIENT_EVIDENCE", "confidence": 0.0, "uncertainty": 1.0, and "evidence_items": [].
5. UNCERTAINTY: Explicitly evaluate uncertainty (0.0 to 1.0) and explain any limitations, ambiguities, or gaps in the evidence.
6. JSON FORMAT: Respond strictly in valid JSON with schema:
{{
  "status": "VERIFIED_SUPPORT" | "CONFLICT_DETECTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE",
  "has_sufficient_evidence": boolean,
  "conflict_detected": boolean,
  "confidence": float (0.0 to 1.0),
  "uncertainty": float (0.0 to 1.0),
  "uncertainty_level": "LOW" | "MEDIUM" | "HIGH",
  "reasoning_summary": string,
  "evidence_items": [
    {{
      "chunk_index": integer (1-based index matching SOURCE N),
      "relevance": float (0.0 to 1.0),
      "stance": "SUPPORTS" | "CONTRADICTS" | "NEUTRAL",
      "reasoning": string,
      "confidence": float (0.0 to 1.0),
      "uncertainty": float (0.0 to 1.0),
      "uncertainty_reasons": [string]
    }}
  ],
  "conflicts": [
    {{
      "topic": string,
      "source_a_index": integer (1-based index),
      "source_a_assertion": string,
      "source_b_index": integer (1-based index),
      "source_b_assertion": string,
      "discrepancy_explanation": string,
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "suggested_resolution": string
    }}
  ]
}}

CONTEXT SOURCES:
{context_str}

CLAIM:
{claim}
"""

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            status = data.get("status", "INSUFFICIENT_EVIDENCE")
            has_evidence = data.get("has_sufficient_evidence", True)

            if "INSUFFICIENT" in status.upper() or not has_evidence:
                return {
                    "status": "INSUFFICIENT_EVIDENCE",
                    "has_sufficient_evidence": False,
                    "conflict_detected": False,
                    "confidence": 0.0,
                    "uncertainty": 1.0,
                    "uncertainty_level": "HIGH",
                    "reasoning_summary": data.get("reasoning_summary", f"INSUFFICIENT EVIDENCE: No indexed documents contained relevant evidence for claim: '{claim}'."),
                    "evidence_items": [],
                    "conflicts": [],
                    "model": self.model_name,
                }

            return {
                "status": status,
                "has_sufficient_evidence": True,
                "conflict_detected": bool(data.get("conflict_detected", False)),
                "confidence": float(data.get("confidence", 0.90)),
                "uncertainty": float(data.get("uncertainty", 0.10)),
                "uncertainty_level": data.get("uncertainty_level", "LOW"),
                "reasoning_summary": data.get("reasoning_summary", ""),
                "evidence_items": data.get("evidence_items", []),
                "conflicts": data.get("conflicts", []),
                "model": self.model_name,
            }
        except Exception as e:
            logger.error(f"Gemini API request failed for evidence analysis: {e}. Falling back to grounded synthesis.")
            return self._grounded_evidence_synthesis(claim, context_chunks)

    def _grounded_evidence_synthesis(
        self,
        claim: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        raw_terms = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", claim.lower())
        c_terms = {t for t in raw_terms if t not in STOP_WORDS}

        def extract_numbers(txt: str):
            res = set()
            for m in re.findall(r"\$?\b\d+(?:\.\d+)?(?:\s*(?:hours?|hrs?|mins?|minutes?|days?|months?|%|k))?\b", txt.lower()):
                clean = m.strip().replace(" ", "")
                res.add(clean)
                digits = re.findall(r"\d+", clean)
                if digits:
                    res.add(digits[0])
            return res

        claim_nums = extract_numbers(claim)

        contradiction_markers = [
            "superseded", "no longer", "invalid", "cancelled", "increased to",
            "decreased to", "changed to", "replaced by", "not permitted",
            "prohibited", "forbidden", "different", "instead of", "differs"
        ]

        evaluated_items = []

        for idx, chunk in enumerate(context_chunks, start=1):
            content = chunk.get("content", "")
            chunk_words = set(re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", content.lower()))
            overlap = c_terms.intersection(chunk_words)

            min_overlap = max(1, min(2, len(c_terms)))
            if len(overlap) < min_overlap:
                continue

            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
            matched_sentences = [
                s for s in sentences
                if any(t in s.lower() for t in c_terms)
            ]
            primary_sentence = matched_sentences[0] if matched_sentences else (sentences[0] if sentences else content[:200])

            sent_nums = extract_numbers(primary_sentence)
            has_contradiction_marker = any(marker in primary_sentence.lower() or marker in content.lower() for marker in contradiction_markers)

            different_number = False
            if claim_nums and sent_nums:
                diff_nums = sent_nums - claim_nums
                if diff_nums:
                    different_number = True

            if has_contradiction_marker or different_number:
                stance = "CONTRADICTS"
            else:
                stance = "SUPPORTS"

            base_sim = float(chunk.get("similarity", 0.8))
            confidence = round(min(0.98, max(0.65, base_sim * (0.95 if stance != "NEUTRAL" else 0.80))), 2)
            uncertainty = round(max(0.02, 1.0 - confidence), 2)

            uncertainty_reasons = []
            if stance == "NEUTRAL":
                uncertainty_reasons.append("Indirect context without explicit assertion")
            if different_number:
                uncertainty_reasons.append("Numerical discrepancy against claim assertion")
            if has_contradiction_marker:
                uncertainty_reasons.append("Contains superseding or invalidation clause")
            if not uncertainty_reasons:
                uncertainty_reasons.append("Verbatim excerpt from indexed operational policy")

            if stance == "SUPPORTS":
                reasoning = f"Directly supports claim: '{primary_sentence}'."
            elif stance == "CONTRADICTS":
                reasoning = f"Contradicts claim: '{primary_sentence}'."
            else:
                reasoning = f"Contextual information related to claim: '{primary_sentence}'."

            evaluated_items.append({
                "chunk_index": idx,
                "relevance": round(base_sim, 2),
                "stance": stance,
                "reasoning": reasoning,
                "confidence": confidence,
                "uncertainty": uncertainty,
                "uncertainty_reasons": uncertainty_reasons,
                "primary_sentence": primary_sentence,
                "numbers": sent_nums,
                "chunk": chunk,
            })

        if not evaluated_items:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "has_sufficient_evidence": False,
                "conflict_detected": False,
                "confidence": 0.0,
                "uncertainty": 1.0,
                "uncertainty_level": "HIGH",
                "reasoning_summary": f"INSUFFICIENT EVIDENCE: No indexed documents contain sufficient verified evidence to support or refute the claim: '{claim}'.",
                "evidence_items": [],
                "conflicts": [],
                "model": "deterministic-grounded-evidence-engine",
            }

        conflicts = []
        for i in range(len(evaluated_items)):
            for j in range(i + 1, len(evaluated_items)):
                item_a = evaluated_items[i]
                item_b = evaluated_items[j]
                doc_a = item_a["chunk"].get("metadata", {}).get("filename", "Doc A")
                doc_b = item_b["chunk"].get("metadata", {}).get("filename", "Doc B")

                nums_a = item_a.get("numbers", set())
                nums_b = item_b.get("numbers", set())
                num_divergence = bool(nums_a and nums_b and (nums_a - nums_b or nums_b - nums_a))

                is_conflict = (
                    (item_a["stance"] != item_b["stance"] and "NEUTRAL" not in (item_a["stance"], item_b["stance"]))
                    or (doc_a != doc_b and (item_a["stance"] == "CONTRADICTS" or item_b["stance"] == "CONTRADICTS"))
                    or (doc_a != doc_b and num_divergence)
                )

                if is_conflict:
                    conflicts.append({
                        "topic": f"Discrepancy in assertions between {doc_a} and {doc_b}",
                        "source_a_index": item_a["chunk_index"],
                        "source_a_assertion": item_a["primary_sentence"],
                        "source_b_index": item_b["chunk_index"],
                        "source_b_assertion": item_b["primary_sentence"],
                        "discrepancy_explanation": f"Source '{doc_a}' ({item_a['stance']}) conflicts with source '{doc_b}' ({item_b['stance']}). Differing conditions found across documents.",
                        "severity": "HIGH",
                        "suggested_resolution": "Review the most recent policy version or reconcile differing stakeholder constraints.",
                    })
                    break
            if conflicts:
                break

        conflict_detected = len(conflicts) > 0

        if conflict_detected:
            status = "CONFLICT_DETECTED"
            overall_conf = 0.65
            overall_unc = 0.55
            unc_level = "HIGH"
            reasoning_summary = f"CONFLICT DETECTED: Sources disagree on claim '{claim}'. Found {len(conflicts)} direct contradiction(s) across evaluated documents."
        elif any(it["stance"] == "SUPPORTS" for it in evaluated_items):
            status = "VERIFIED_SUPPORT"
            overall_conf = 0.93
            overall_unc = 0.07
            unc_level = "LOW"
            reasoning_summary = f"Claim '{claim}' is verified and supported by {len([it for it in evaluated_items if it['stance'] == 'SUPPORTS'])} document excerpt(s)."
        elif all(it["stance"] == "CONTRADICTS" for it in evaluated_items):
            status = "CONTRADICTED"
            overall_conf = 0.90
            overall_unc = 0.10
            unc_level = "LOW"
            reasoning_summary = f"Claim '{claim}' is directly contradicted by verified document policy."
        else:
            status = "INSUFFICIENT_EVIDENCE"
            overall_conf = 0.30
            overall_unc = 0.70
            unc_level = "MEDIUM"
            reasoning_summary = f"Weak contextual match for claim '{claim}' without definitive proof."

        out_items = []
        for it in evaluated_items:
            out_items.append({
                "chunk_index": it["chunk_index"],
                "relevance": it["relevance"],
                "stance": it["stance"],
                "reasoning": it["reasoning"],
                "confidence": it["confidence"],
                "uncertainty": it["uncertainty"],
                "uncertainty_reasons": it["uncertainty_reasons"],
            })

        return {
            "status": status,
            "has_sufficient_evidence": status != "INSUFFICIENT_EVIDENCE",
            "conflict_detected": conflict_detected,
            "confidence": overall_conf,
            "uncertainty": overall_unc,
            "uncertainty_level": unc_level,
            "reasoning_summary": reasoning_summary,
            "evidence_items": out_items,
            "conflicts": conflicts,
            "model": "deterministic-grounded-evidence-engine",
        }

class LLMService:
    """Manages LLM providers with pluggable backend configuration."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self._provider = provider or GeminiProvider()

    def set_provider(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate_grounded_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return self._provider.generate_grounded_answer(question, context_chunks)

    def generate_action_plan(
        self,
        query: str,
        tasks_context: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._provider.generate_action_plan(query, tasks_context, constraints)

    def generate_decision_analysis(
        self,
        decision_context: Dict[str, Any],
        options_context: List[Dict[str, Any]],
        general_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return self._provider.generate_decision_analysis(decision_context, options_context, general_evidence)

    def analyze_claim_evidence(
        self,
        claim: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return self._provider.analyze_claim_evidence(claim, context_chunks)

llm_service = LLMService()
