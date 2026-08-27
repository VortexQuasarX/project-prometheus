"""Evaluator Agent: rule-based response scoring (DECISIONS B14).

Metrics: relevance, groundedness, safety, completeness, cost efficiency.
Overall = weighted mean (0.25 / 0.25 / 0.2 / 0.15 / 0.15); passed iff
overall >= 0.7.

Pure logic; no DB access. Production path (judge LLM) is a drop-in
replacement with the same return type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_WORD_RE = re.compile(r"[a-z0-9']+")

WEIGHTS = {
    "relevance": 0.25,
    "groundedness": 0.25,
    "safety": 0.20,
    "completeness": 0.15,
    "cost_efficiency": 0.15,
}

PASS_THRESHOLD = 0.7


@dataclass
class EvalResult:
    """Evaluation result (fixed interface, spec shape)."""

    request_id: str
    relevance_score: float
    groundedness_score: float
    safety_score: float
    completeness_score: float
    cost_efficiency_score: float
    overall_score: float
    passed: bool
    feedback: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "relevance_score": self.relevance_score,
            "groundedness_score": self.groundedness_score,
            "safety_score": self.safety_score,
            "completeness_score": self.completeness_score,
            "cost_efficiency_score": self.cost_efficiency_score,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "feedback": self.feedback,
        }


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def _relevance(query: str, answer: str) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    a_tokens = _tokenize(answer)
    overlap = len(q_tokens & a_tokens)
    return round(min(1.0, overlap / len(q_tokens) + 0.1), 4)


def _groundedness(citations: list[dict[str, Any]] | None, answer: str) -> float:
    citations = citations or []
    if citations:
        return 1.0
    lower = (answer or "").lower()
    if any(marker in lower for marker in ("source:", "per the document", "according to", "context")):
        return 0.5
    return 0.0


def _safety(router_decision: str) -> float:
    return 0.0 if router_decision == "REJECT" else 1.0


def _completeness(query: str, answer: str) -> float:
    q_words = len(_WORD_RE.findall(query or ""))
    a_words = len(_WORD_RE.findall(answer or ""))
    target = max(8, int(q_words * 1.5))
    if a_words == 0:
        return 0.0
    return round(min(1.0, a_words / target), 4)


def _cost_efficiency(cost_usd: float, request_budget_usd: float) -> float:
    if request_budget_usd <= 0:
        return 1.0 if cost_usd <= 0 else 0.0
    return round(max(0.0, 1.0 - min(1.0, cost_usd / request_budget_usd)), 4)


def evaluate(
    *,
    request_id: str,
    query: str,
    answer: str,
    citations: list[dict[str, Any]] | None,
    cost_usd: float,
    model: str,
    router_decision: str,
    input_tokens: int,
    output_tokens: int,
    policy: dict[str, Any],
) -> EvalResult:
    """Score a chat response with deterministic rules."""
    relevance = _relevance(query, answer)
    groundedness = _groundedness(citations, answer)
    safety = _safety(router_decision)
    request_budget = float(policy.get("request_budget_usd", 0.05))
    completeness = _completeness(query, answer)
    cost_efficiency = _cost_efficiency(cost_usd, request_budget)

    overall = round(
        relevance * WEIGHTS["relevance"]
        + groundedness * WEIGHTS["groundedness"]
        + safety * WEIGHTS["safety"]
        + completeness * WEIGHTS["completeness"]
        + cost_efficiency * WEIGHTS["cost_efficiency"],
        4,
    )
    passed = overall >= PASS_THRESHOLD

    feedback_parts: list[str] = []
    if relevance < 0.5:
        feedback_parts.append("answer has low token overlap with the query")
    if groundedness == 0.0:
        feedback_parts.append("answer is not grounded in retrieved context (no citations)")
    if safety < 1.0:
        feedback_parts.append("request was rejected by guardrails")
    if completeness < 0.5:
        feedback_parts.append("answer is short relative to query complexity")
    if cost_efficiency < 0.5:
        feedback_parts.append(f"cost {cost_usd:.4f} USD is high vs request budget {request_budget:.4f} USD")
    feedback = (
        "; ".join(feedback_parts) if feedback_parts else "all rule-based checks passed"
    )
    if not passed:
        feedback = f"[evaluation failed] {feedback}"

    return EvalResult(
        request_id=request_id,
        relevance_score=relevance,
        groundedness_score=groundedness,
        safety_score=safety,
        completeness_score=completeness,
        cost_efficiency_score=cost_efficiency,
        overall_score=overall,
        passed=passed,
        feedback=feedback,
        metadata={
            "model": model,
            "router_decision": router_decision,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "citations": len(citations or []),
        },
    )


__all__ = ["EvalResult", "evaluate", "WEIGHTS", "PASS_THRESHOLD"]
