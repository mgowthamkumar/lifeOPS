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

llm_service = LLMService()
