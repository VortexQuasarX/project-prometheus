"""Agent planner: builds the plan (step descriptors) for an agent run.

The plan is a list of ``{"name": ..., "description": ...}`` dicts that the
orchestrator stores on ``AgentRun.plan`` and that the frontend renders as the
run's step list.
"""

from __future__ import annotations

from typing import Any

PLANS: dict[str, dict[str, list[dict[str, str]]]] = {
    "finops": {
        "steps": [
            {"name": "gather_metrics", "description": "Collect usage, cache, cost and latency metrics via tools."},
            {"name": "detect_inefficiency", "description": "Detect inefficiency from trigger + observed metrics."},
            {"name": "generate_hypotheses", "description": "Generate hypotheses from observations."},
            {"name": "simulate_routing_policy", "description": "Simulate routing policy changes."},
            {"name": "simulate_cache_threshold", "description": "Simulate cache threshold changes."},
            {"name": "estimate_savings", "description": "Estimate expected monthly savings."},
            {"name": "assess_risk", "description": "Assess risk level and latency impact of the change."},
            {"name": "create_action_plan", "description": "Create AgentAction rows for human approval."},
            {"name": "request_human_approval", "description": "Pause run for human approval (or auto-apply)."},
            {"name": "apply_local_policy", "description": "Apply the approved policy delta."},
            {"name": "verify_outcome", "description": "Mark run verified; await subsequent request metrics."},
            {"name": "write_audit_event", "description": "Write the audit trail entry."},
        ]
    },
    "reliability": {
        "steps": [
            {"name": "gather_stats", "description": "Gather latency, error and failure statistics."},
            {"name": "detect_anomalies", "description": "Detect latency spikes, provider errors, cache/retrieval failures, budget anomalies, repeated failures."},
            {"name": "recommend_fallback", "description": "Recommend a fallback model."},
            {"name": "recommend_cache_only", "description": "Recommend cache-only mode when appropriate."},
            {"name": "recommend_retry_policy", "description": "Recommend retry policy changes."},
            {"name": "create_alerts", "description": "Write reliability alerts to the alert table."},
            {"name": "write_audit_event", "description": "Write the audit trail entry."},
        ]
    },
    "evaluator": {
        "steps": [
            {"name": "load_request", "description": "Load the request/response pair to evaluate."},
            {"name": "score_relevance", "description": "Score relevance via token overlap."},
            {"name": "score_groundedness", "description": "Score groundedness from citations."},
            {"name": "score_safety", "description": "Score safety from guardrail outcome."},
            {"name": "score_completeness", "description": "Score completeness from answer length."},
            {"name": "score_cost_efficiency", "description": "Score cost efficiency vs request budget."},
            {"name": "aggregate", "description": "Compute weighted overall score and pass decision."},
            {"name": "report", "description": "Persist evaluation result."},
        ]
    },
    "guardrail": {
        "steps": [
            {"name": "preflight_check", "description": "Run PII, unsafe, injection, restricted-topic and policy checks."},
            {"name": "mask_pii", "description": "Mask PII when masking is enabled."},
            {"name": "classify_risk", "description": "Classify risk level and blocking decision."},
            {"name": "report", "description": "Persist guardrail result."},
        ]
    },
    "router": {
        "steps": [
            {"name": "classify_query", "description": "Classify category, complexity and risk."},
            {"name": "decide_route", "description": "Map to one of the six router decisions."},
            {"name": "pick_model", "description": "Pick the target model for LLM decisions."},
            {"name": "report", "description": "Persist router decision."},
        ]
    },
}

DEFAULT_PLAN = [
    {"name": "gather_metrics", "description": "Collect metrics."},
    {"name": "analyze", "description": "Analyze observations."},
    {"name": "report", "description": "Persist outcome."},
]


def build_plan(agent_type: str, trigger: str) -> list[dict[str, str]]:
    """Return plan step descriptors ``[{name, description}, ...]``."""
    plan_def = PLANS.get(agent_type)
    if plan_def is None:
        return list(DEFAULT_PLAN)
    return list(plan_def["steps"])


def build_hypotheses(agent_type: str, trigger: str, observations: dict[str, Any]) -> list[dict[str, str]]:
    """Build hypothesis descriptors from trigger + observations (FinOps step 3)."""
    trigger_hypotheses: dict[str, str] = {
        "budget_threshold": "Recent spend is consuming the daily budget faster than planned.",
        "cache_hit_rate_low": "Cache hit rate is below 0.5; repeated queries are likely paying full LLM cost.",
        "expensive_model_overuse": "Expensive models are being selected more than the daily limit allows.",
        "repeated_similar_queries": "Similar queries recur; they could be served from cache.",
        "latency_increasing": "Latency p95 is trending up; routing or provider choice may need adjustment.",
        "manual": "Manual optimize requested; evaluate routing, caching and model mix.",
    }
    hypothesis = trigger_hypotheses.get(trigger, "Operational inefficiency detected from metrics.")
    hypotheses: list[dict[str, str]] = [
        {
            "hypothesis": hypothesis,
            "evidence": _evidence_for(trigger, observations),
            "test": "Simulate policy change and compare estimated cost.",
        },
        {
            "hypothesis": "Routing simple queries to cheaper models reduces cost without quality loss.",
            "evidence": _evidence_for("routing", observations),
            "test": "simulate_routing_policy",
        },
        {
            "hypothesis": "A higher cache similarity threshold trades a small hit-rate loss for large savings.",
            "evidence": _evidence_for("cache", observations),
            "test": "simulate_cache_threshold",
        },
    ]
    return hypotheses


def _evidence_for(kind: str, observations: dict[str, Any]) -> str:
    summary: list[str] = []
    if kind in ("budget_threshold", "routing", "cache", "manual"):
        budget = observations.get("budget_status")
        if budget:
            summary.append(f"budget_status={budget}")
        hit_rate = observations.get("cache_hit_rate")
        if hit_rate is not None:
            summary.append(f"cache_hit_rate={hit_rate}")
        model_costs = observations.get("model_costs") or []
        if model_costs:
            entries: list[dict[str, Any]] = []
            if isinstance(model_costs, dict):
                inner = model_costs.get("model_costs")
                if isinstance(inner, list):
                    entries = [e for e in inner if isinstance(e, dict)]
                else:
                    numeric = {
                        k: v
                        for k, v in model_costs.items()
                        if isinstance(v, (int, float))
                    }
                    if numeric:
                        top_model = max(numeric, key=lambda k: float(numeric[k]))
                        summary.append(
                            f"top_spend_model={top_model} cost={numeric[top_model]}"
                        )
            else:
                entries = [e for e in model_costs if isinstance(e, dict)]
            if entries:
                top = max(entries, key=lambda e: float(e.get("cost_usd") or 0.0))
                summary.append(f"top_spend_model={top.get('model')} cost={top.get('cost_usd')}")
        latency = observations.get("latency")
        if latency:
            summary.append(f"latency_p95={latency.get('p95_ms')}")
    return "; ".join(summary) if summary else "no metrics recorded"


__all__ = ["build_plan", "build_hypotheses"]
