"""Cacheability policy: what MAY be stored in the semantic cache.

Refusals, blocked requests, PII-masked content and non-router-eligible
decisions are never cached; only guardrail-passed CHEAP_MODEL/STRONG_MODEL
responses whose evaluation passed (or is disabled) qualify (DECISIONS B10:
"Never cache refusals/blocked responses").
"""
from __future__ import annotations

from typing import Any

__all__ = ["PASSED_GUARDRAIL_STATUSES", "CACHEABLE_ROUTER_DECISIONS", "should_cache"]

#: Router decisions whose responses are cacheable.
CACHEABLE_ROUTER_DECISIONS = frozenset({"CHEAP_MODEL", "STRONG_MODEL"})

#: Guardrail statuses that mean "passed" (anything else is not cached —
#: blocked, masked/PII, unknown).
PASSED_GUARDRAIL_STATUSES = frozenset({"passed", "ok", "clean"})


def should_cache(
    router_decision: str,
    guardrail_status: str,
    evaluation_passed: bool | None,
    policy: dict[str, Any],
) -> bool:
    """Decide whether a chat response may be written to the semantic cache.

    ``evaluation_passed`` is ``True`` when the evaluator passed the response,
    ``False`` when it failed, and ``None`` when evaluation was not run.
    When ``policy.require_evaluation`` is true, ``None``/``False`` means the
    response is not cacheable; when evaluation is disabled, it is cacheable.
    """
    decision = (router_decision or "").strip().upper()
    if decision not in CACHEABLE_ROUTER_DECISIONS:
        return False

    status = (guardrail_status or "").strip().lower()
    if status not in PASSED_GUARDRAIL_STATUSES:
        # blocked / rejected / masked / unknown -> never cache
        return False

    if not bool(policy.get("require_cache_check", True)):
        return False

    if bool(policy.get("require_evaluation", True)):
        if evaluation_passed is not True:
            return False

    return True
