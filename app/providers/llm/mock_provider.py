"""Deterministic mock LLM provider.

Grounds answers in retrieved context chunks (citation markers [1], [2] ...
mapped to chunk order), falls back to a small internal knowledge base about
the five seed topics, and refuses gracefully for unrelated queries.

Determinism contract (DECISIONS B9/B12, task brief):
- token simulation: ``input_tokens = max(1, len(prompt)//4)``,
  ``output_tokens = max(1, len(answer)//4)``
- latency: cheap models -> ``settings.mock_latency_cheap_ms`` (default 100),
  strong models -> ``settings.mock_latency_strong_ms`` (default 500)
- never uses randomness: identical inputs produce identical outputs across
  processes and restarts.

RAG context is passed through the extra ``context`` keyword argument (a list
of chunk dicts as produced by ``app.rag.retriever.Retriever.retrieve``:
``{document_id, chunk_id, content, score, metadata}``), or via
:meth:`MockLLMProvider.set_context`. When no context is provided the
provider answers from its internal knowledge base. The pipeline builder
should pass retrieved chunks via ``context=`` for grounded, cited answers.
"""
from __future__ import annotations

import re
from typing import Any

from app.providers import get_setting
from app.providers.llm.base import LLMProvider, LLMResponse

__all__ = ["MockLLMProvider"]

# ---------------------------------------------------------------------------
# Internal knowledge base: one grounded fact-block per seed topic so that
# context-free queries still produce accurate, demo-facing answers.
# ---------------------------------------------------------------------------
_KB_TOPICS: list[dict[str, Any]] = [
    {
        "topic": "AI Cost Governance",
        "keywords": ("cost", "govern", "budget", "spend", "allocate", "chargeback", "showback"),
        "text": (
            "AI cost governance couples budgets, policies and observability so every model call is "
            "accountable to a business owner. Daily budgets with warning, critical and exceeded "
            "states, request-level budget caps, per-model spend tracking and audited policy changes "
            "keep runaway token spend in check. Governance is only effective when cost data is "
            "attributed per team, model and use case, so chargeback and showback feed the FinOps "
            "conversation."
        ),
    },
    {
        "topic": "LLM Cache Optimization",
        "keywords": ("cache", "caching", "semantic", "similarity", "hit", "ttl", "repeat"),
        "text": (
            "Semantic caching stores prior LLM answers keyed by embedding similarity instead of "
            "exact text match, so near-duplicate questions reuse the previous response. Entries are "
            "matched against a similarity threshold such as 0.82, expire after a TTL, and are "
            "invalidated when the policy version or knowledge-base version changes. High hit rates "
            "cut token spend and latency while the cache-write cost stays a small fraction of a full "
            "generation."
        ),
    },
    {
        "topic": "AWS Bedrock Cost Controls",
        "keywords": ("bedrock", "aws", "haiku", "sonnet", "titan", "provisioned", "on-demand", "region"),
        "text": (
            "Amazon Bedrock bills per token on demand, with model classes spanning the cheap Haiku "
            "tier to stronger Sonnet-class models and Titan embedding models. Cost controls include "
            "model routing to the cheapest adequate tier, on-demand versus provisioned throughput "
            "choices, cross-region inference profiles for resilience, and CloudWatch alarms wired to "
            "budgets. A gateway should never call an expensive model when a cheap one satisfies the "
            "request."
        ),
    },
    {
        "topic": "AI Guardrails Overview",
        "keywords": ("guardrail", "safety", "pii", "injection", "safe", "harm", "privacy", "mask"),
        "text": (
            "AI guardrails apply policy before and after model calls: PII detection with masking, "
            "unsafe-content screening, prompt-injection detection, restricted-topic blocks and "
            "output filtering. Blocked requests return a safe refusal without invoking an expensive "
            "model, and every decision is written to the audit trail. Guardrails protect the "
            "organization, not just the model, and must never be silently bypassed."
        ),
    },
    {
        "topic": "FinOps for AI",
        "keywords": ("finops", "fin-ops", "fin ops", "unit", "econ", "waste", "efficiency", "cloud finance"),
        "text": (
            "FinOps for AI applies the inform, optimize, operate cycle to model spend: measure unit "
            "economics per query, route to cheaper models, raise cache hit rates, retire unused "
            "capacity and forecast demand. Continuous optimization turns a cost center into a "
            "governed, efficient platform, and every saving is verified after the policy lands."
        ),
    },
]

_FALLBACK_ANSWER = (
    "I don't have enough context to answer that question accurately. Try asking about AI cost "
    "governance, LLM cache optimization, AWS Bedrock cost controls, AI guardrails, or FinOps for AI."
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class MockLLMProvider(LLMProvider):
    """Deterministic, grounded, context-aware mock LLM backend."""

    provider_name = "mock"

    def __init__(self) -> None:
        self._context: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # context injection (extra channel beyond the fixed generate signature)
    # ------------------------------------------------------------------
    def set_context(self, chunks: list[dict[str, Any]] | None) -> None:
        """Set (or clear) the RAG context used for subsequent generations."""
        self._context = list(chunks or [])

    def clear_context(self) -> None:
        """Clear the RAG context set via :meth:`set_context`."""
        self._context = []

    # ------------------------------------------------------------------
    # LLMProvider
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        model: str,
        *,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
        context: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Generate a deterministic grounded answer.

        ``context`` is the preferred channel for RAG chunks; when omitted the
        chunks set via :meth:`set_context` are used. ``temperature`` is
        accepted for interface parity and ignored (outputs are deterministic).
        """
        del system  # reserved for interface parity; mock grounding comes from context
        resolved_model = self._resolve_model(model)
        strong = resolved_model == "mock-large"

        chunks = self._usable_chunks(context if context is not None else self._context, strong)
        answer = self._compose_answer(prompt, chunks, strong)

        if max_tokens and max_tokens > 0 and len(answer) > max_tokens * 4:
            answer = self._truncate(answer, max_tokens * 4)

        return LLMResponse(
            text=answer,
            model=resolved_model,
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(answer) // 4),
            latency_ms=self._latency_ms(strong),
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _resolve_model(self, model: str | None) -> str:
        """Resolve a model name to mock-small/mock-large.

        Unknown names fall back to ``settings.default_model`` (contract).
        """
        default_model = (get_setting("default_model", "mock-small") or "mock-small").strip().lower()
        candidate = (model or default_model).strip().lower()
        if candidate in {"mock-small", "mock-cheap", "small", "cheap"}:
            return "mock-small"
        if candidate in {"mock-large", "mock-strong", "large", "strong"}:
            return "mock-large"
        # Unknown model -> fall back to settings.default_model.
        if default_model in {"mock-large", "mock-strong", "large", "strong"}:
            return "mock-large"
        return "mock-small"

    def _usable_chunks(self, chunks: list[dict[str, Any]] | None, strong: bool) -> list[dict[str, Any]]:
        usable = [c for c in (chunks or []) if isinstance(c, dict) and (c.get("content") or "")]
        # Strong models ground on more chunks; cheap models stay short.
        return usable[: 4 if strong else 2]

    def _compose_answer(self, prompt: str, chunks: list[dict[str, Any]], strong: bool) -> str:
        if not chunks:
            return self._answer_from_kb(prompt)

        lines: list[str] = []
        lines.append(
            "Here is a detailed answer grounded in the retrieved context."
            if strong
            else "Here is a concise answer drawn from the retrieved context."
        )
        for i, chunk in enumerate(chunks, start=1):
            sentences = self._sentences(chunk.get("content") or "", limit=2 if strong else 1)
            for sentence in sentences:
                lines.append(f"{sentence} [{i}]")
        lines.append(f"In summary, {self._synthesis(chunks[0])}")
        sources = "; ".join(self._source_ref(i, c) for i, c in enumerate(chunks, start=1))
        lines.append(f"Sources: {sources}.")
        return "\n".join(lines)

    def _answer_from_kb(self, prompt: str) -> str:
        lowered = prompt.lower()
        for topic in _KB_TOPICS:
            if any(keyword in lowered for keyword in topic["keywords"]):
                return (
                    f"{topic['text']} (per Project Prometheus seed content on {topic['topic']}.)"
                )
        return _FALLBACK_ANSWER

    @staticmethod
    def _sentences(content: str, limit: int = 1) -> list[str]:
        sentences: list[str] = []
        for raw in _SENTENCE_SPLIT_RE.split(content):
            sentence = " ".join(raw.strip().split())
            if not sentence:
                continue
            sentence = sentence[:240].rstrip()
            if sentence and not sentence.endswith((".", "!", "?")):
                sentence += "."
            sentences.append(sentence)
            if len(sentences) >= limit:
                break
        return sentences

    @staticmethod
    def _synthesis(chunk: dict[str, Any]) -> str:
        first = MockLLMProvider._sentences(chunk.get("content") or "", limit=1)
        if first:
            return f"the key point is: {first[0][:160].rstrip('.')}."
        return "the answer above reflects the retrieved context."

    @staticmethod
    def _source_ref(index: int, chunk: dict[str, Any]) -> str:
        metadata = chunk.get("metadata") or {}
        title = chunk.get("title") or metadata.get("title") or "document"
        chunk_id = chunk.get("chunk_id") or "chunk"
        return f"[{index}] {title} ({chunk_id})"

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        cut = text[:limit]
        if " " in cut:
            cut = cut[: cut.rfind(" ")]
        return cut.rstrip() + " …"

    @staticmethod
    def _latency_ms(strong: bool) -> int:
        if strong:
            return max(0, int(get_setting("mock_latency_strong_ms", 500) or 500))
        return max(0, int(get_setting("mock_latency_cheap_ms", 100) or 100))
