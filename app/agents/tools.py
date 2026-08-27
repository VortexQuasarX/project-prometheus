"""Agent tool registry (Project Prometheus).

FinOps tools (exactly the 11 spec names) + reliability tools:

  get_usage_metrics, get_cache_stats, get_model_costs, get_latency_report,
  simulate_routing_policy, simulate_cache_threshold, estimate_savings,
  create_action_plan, request_human_approval, apply_local_policy,
  write_audit_event

  recommend_fallback_model, recommend_cache_only, recommend_retry_policy,
  create_alert

Each callable has signature ``(run_id: str, input_dict: dict, db) -> dict``.
``run_tool`` wraps the call with wall-clock timing + status and appends an
``AgentToolCall`` row in the exact spec shape:
``{tool, input, output, duration_ms, status}``.

Cross-slice dependencies (db models, governance, cost, observability) are
imported lazily so this module compiles and imports standalone.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

FINOPS_TOOLS: tuple[str, ...] = (
    "get_usage_metrics",
    "get_cache_stats",
    "get_model_costs",
    "get_latency_report",
    "simulate_routing_policy",
    "simulate_cache_threshold",
    "estimate_savings",
    "create_action_plan",
    "request_human_approval",
    "apply_local_policy",
    "write_audit_event",
)

RELIABILITY_TOOLS: tuple[str, ...] = (
    "recommend_fallback_model",
    "recommend_cache_only",
    "recommend_retry_policy",
    "create_alert",
)

# ---------------------------------------------------------------------------
# Lazy cross-slice helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _emit_sse(event_type: str, **payload: Any) -> None:
    """Best-effort SSE outbox emit; no-op when the events module is absent."""
    try:
        from app.core import events  # type: ignore
    except Exception:
        return
    try:
        request_id = payload.pop("request_id", None)
        run_id = payload.pop("run_id", None)
        action_id = payload.pop("action_id", None)
        inner = payload.pop("payload", None)
        body = inner if isinstance(inner, dict) else dict(payload)
        events.emit_sse_event(
            event_type,
            body,
            request_id=request_id if isinstance(request_id, str) else None,
            run_id=run_id if isinstance(run_id, str) else None,
            action_id=action_id if isinstance(action_id, str) else None,
        )
    except Exception:
        return


def _fetch_run(db: Any, run_id: str) -> Any | None:
    try:
        from app.db import models
    except Exception:
        return None
    try:
        return db.query(models.AgentRun).filter(models.AgentRun.run_id == run_id).first()
    except Exception:
        return None


def _usage_rows(db: Any) -> list[Any]:
    try:
        from app.db import models
    except Exception:
        return []
    try:
        return db.query(models.UsageRecord).all()
    except Exception:
        return []


def _request_rows(db: Any) -> list[Any]:
    try:
        from app.db import models
    except Exception:
        return []
    try:
        return db.query(models.Request).all()
    except Exception:
        return []


def _now(dt: Any) -> str:
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


# ---------------------------------------------------------------------------
# FinOps tools
# ---------------------------------------------------------------------------


def get_usage_metrics(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    rows = _usage_rows(db)
    total_cost = sum(float(getattr(r, "cost_usd", 0.0) or 0.0) for r in rows)
    total_input = sum(int(getattr(r, "input_tokens", 0) or 0) for r in rows)
    total_output = sum(int(getattr(r, "output_tokens", 0) or 0) for r in rows)
    requests = _request_rows(db)
    avg_latency = 0.0
    if requests:
        latencies = [float(getattr(r, "latency_ms", 0.0) or 0.0) for r in requests]
        avg_latency = sum(latencies) / len(latencies)
    return {
        "total_requests": len(rows),
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "avg_latency_ms": round(avg_latency, 2),
        "source": "usage_records",
    }


def get_cache_stats(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    requests = _request_rows(db)
    hits = misses = 0
    for r in requests:
        if getattr(r, "cache_hit", None) is True:
            hits += 1
        elif getattr(r, "cache_hit", None) is False:
            misses += 1
    total = hits + misses
    hit_rate = round(hits / total, 4) if total else 0.0
    entry_count = 0
    try:
        from app.db import models

        entry_count = db.query(models.CacheEntry).count()
    except Exception:
        pass
    return {
        "hit_count": hits,
        "miss_count": misses,
        "hit_rate": hit_rate,
        "entry_count": entry_count,
        "source": "requests + cache_entries",
    }


def get_model_costs(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    rows = _usage_rows(db)
    by_model: dict[str, dict[str, float]] = {}
    for r in rows:
        model = str(getattr(r, "model", "unknown") or "unknown")
        cost = float(getattr(r, "cost_usd", 0.0) or 0.0)
        entry = by_model.setdefault(model, {"requests": 0.0, "cost_usd": 0.0, "input_tokens": 0.0, "output_tokens": 0.0})
        entry["requests"] += 1
        entry["cost_usd"] += cost
        entry["input_tokens"] += float(getattr(r, "input_tokens", 0) or 0)
        entry["output_tokens"] += float(getattr(r, "output_tokens", 0) or 0)
    models_list = [
        {"model": m, "requests": int(v["requests"]), "cost_usd": round(v["cost_usd"], 6),
         "input_tokens": int(v["input_tokens"]), "output_tokens": int(v["output_tokens"])}
        for m, v in sorted(by_model.items(), key=lambda kv: kv[1]["cost_usd"], reverse=True)
    ]
    return {"model_costs": models_list, "total_cost_usd": round(sum(v["cost_usd"] for v in by_model.values()), 6)}


def get_latency_report(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    requests = _request_rows(db)
    latencies = sorted(float(getattr(r, "latency_ms", 0.0) or 0.0) for r in requests)
    if not latencies:
        return {"avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "count": 0}
    n = len(latencies)
    avg = sum(latencies) / n
    p95 = latencies[int(n * 0.95) - 1] if n >= 20 else (latencies[-1] if n else 0.0)
    return {
        "avg_ms": round(avg, 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(latencies[-1], 2),
        "count": n,
    }


def simulate_routing_policy(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Estimate savings from shifting expensive-model traffic to cheap models."""
    shift = str(input_dict.get("model_shift", "cheap"))
    fraction = float(input_dict.get("fraction", 0.3))
    model_cost_data = get_model_costs(run_id, {}, db)
    expensive_cost = 0.0
    for m in model_cost_data.get("model_costs", []):
        if m["model"] in ("mock-large", "bedrock-strong"):
            expensive_cost += float(m["cost_usd"])
    if shift == "cheap":
        # Shifting x% of expensive traffic to ~1/4 the price saves ~75% of that leg.
        saving = expensive_cost * fraction * 0.75
        scenario = "shift_expensive_to_cheap"
    else:
        saving = 0.0
        scenario = "no_change"
    return {
        "scenario": scenario,
        "fraction": fraction,
        "estimated_monthly_saving_usd": round(saving * 30, 2),
        "assumptions": "mock-large/bedrock-strong -> mock-small/bedrock-cheap at ~25% cost",
    }


def simulate_cache_threshold(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Estimate hit-rate gain from lowering the cache similarity threshold."""
    current_threshold = float(input_dict.get("current_threshold", 0.82))
    new_threshold = float(input_dict.get("threshold", 0.75))
    stats = get_cache_stats(run_id, {}, db)
    hit_rate = float(stats.get("hit_rate", 0.0))
    if new_threshold >= current_threshold:
        gain = 0.0
    else:
        # Rough linear heuristic: every 0.01 of threshold slack adds ~1% hit rate.
        gain = min(0.5, (current_threshold - new_threshold) * 1.0 * (1.0 - hit_rate))
    estimated_hit_rate = round(min(0.99, hit_rate + gain), 4)
    return {
        "current_threshold": current_threshold,
        "proposed_threshold": new_threshold,
        "current_hit_rate": hit_rate,
        "estimated_hit_rate": estimated_hit_rate,
        "estimated_hit_gain": round(gain, 4),
        "note": "heuristic estimate; validate on real traffic",
    }


def estimate_savings(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Combine simulated savings legs into one monthly estimate."""
    routing = float(input_dict.get("routing_saving_usd", 0.0))
    cache = float(input_dict.get("cache_saving_usd", 0.0))
    total = round(routing + cache, 2)
    return {
        "expected_monthly_saving_usd": total,
        "routing_saving_usd": round(routing, 2),
        "cache_saving_usd": round(cache, 2),
        "confidence": "medium",
    }


def create_action_plan(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Create an AgentAction row (delegates to governance.approvals)."""
    try:
        from app.governance.approvals import create_action
    except Exception as exc:
        return {"error": f"approvals module unavailable: {exc}", "created": False}
    title = str(input_dict.get("title", "Optimize model routing"))
    saving = float(input_dict.get("expected_monthly_saving_usd", 0.0))
    risk = str(input_dict.get("risk_level", "low"))
    latency = str(input_dict.get("latency_impact", "minimal"))
    policy_delta = dict(input_dict.get("policy_delta") or {})
    approval_required = bool(input_dict.get("approval_required", True))
    try:
        action = create_action(
            run_id=run_id,
            title=title,
            expected_monthly_saving_usd=saving,
            risk_level=risk,
            latency_impact=latency,
            policy_delta=policy_delta,
            approval_required=approval_required,
        )
        return {
            "created": True,
            "action_id": action.action_id,
            "title": action.title,
            "expected_monthly_saving_usd": action.expected_monthly_saving_usd,
            "risk_level": action.risk_level,
            "latency_impact": action.latency_impact,
            "approval_required": action.approval_required,
            "status": action.status,
        }
    except Exception as exc:
        return {"error": str(exc), "created": False}


def request_human_approval(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    run = _fetch_run(db, run_id)
    if run is not None:
        try:
            run.status = "waiting_approval"
            run.approval_status = "pending"
            db.commit()
        except Exception:
            db.rollback()
    action_ids = input_dict.get("action_ids") or []
    _emit_sse("action_pending_approval", run_id=run_id, payload={"action_ids": action_ids})
    return {"run_id": run_id, "status": "waiting_approval", "action_ids": action_ids}


def apply_local_policy(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Merge a policy delta into the active policy (local mode)."""
    policy_delta = dict(input_dict.get("policy_delta") or {})
    actor = str(input_dict.get("actor", "finops_agent"))
    try:
        from app.governance.policy_engine import get_policy, update_policy

        current, version = get_policy()
        merged = {**current, **policy_delta}
        new_body, new_version = update_policy(merged, actor=actor, reason="agent action applied")
    except Exception as exc:
        return {"applied": False, "error": str(exc)}
    run = _fetch_run(db, run_id)
    if run is not None:
        try:
            run.status = "applied"
            run.approval_status = "approved"
            db.commit()
        except Exception:
            db.rollback()
    _emit_sse("action_applied", run_id=run_id, payload={"policy_version": new_version})
    return {"applied": True, "policy_version": new_version, "policy": new_body}


def write_audit_event(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    try:
        from app.governance.audit import append

        action = str(input_dict.get("action", "agent.tool.write_audit_event"))
        resource = str(input_dict.get("resource", run_id))
        actor = str(input_dict.get("actor", "agent"))
        role = str(input_dict.get("role", "system"))
        metadata = dict(input_dict.get("metadata") or {})
        event = append(actor=actor, role=role, action=action, resource=resource, metadata=metadata)
        return {"written": True, "event_id": event.event_id}
    except Exception as exc:
        return {"written": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Reliability tools
# ---------------------------------------------------------------------------

_FALLBACK_MAP = {
    "mock-large": "mock-small",
    "bedrock-strong": "bedrock-cheap",
    "bedrock-cheap": "mock-small",
    "mock-small": "mock-small",
}


def recommend_fallback_model(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    model = str(input_dict.get("model", "mock-large"))
    fallback = _FALLBACK_MAP.get(model, "mock-small")
    return {
        "fallback_model": fallback,
        "reason": f"{model} unavailable or failing; fall back to {fallback}",
    }


def recommend_cache_only(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    reason = str(input_dict.get("reason", "provider instability detected"))
    return {
        "recommendation": "enable cache_only kill-switch mode",
        "reason": reason,
        "impact": "cache misses return no-LLM refusal until stability returns",
    }


def recommend_retry_policy(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    max_retries = int(input_dict.get("max_retries", 2))
    base_backoff = float(input_dict.get("base_backoff_seconds", 1.0))
    return {
        "retry_policy": {
            "max_retries": max_retries,
            "base_backoff_seconds": base_backoff,
            "backoff_multiplier": 2.0,
        },
        "reason": "provider errors observed; exponential backoff recommended",
    }


def create_alert(run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    alert_type = str(input_dict.get("alert_type", "reliability_generic"))
    severity = str(input_dict.get("severity", "warning"))
    message = str(input_dict.get("message", "Reliability alert"))
    metadata = dict(input_dict.get("metadata") or {})
    try:
        from app.db import models

        alert = models.BudgetAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=metadata,
            acknowledged=False,
            created_at=datetime.now(UTC),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return {"alert_id": getattr(alert, "id", None), "alert_type": alert_type, "created_at": _now_iso()}
    except Exception as exc:
        return {"error": str(exc), "created": False}


# ---------------------------------------------------------------------------
# Registry + runner
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Callable[[str, dict[str, Any], Any], dict[str, Any]]] = {
    "get_usage_metrics": get_usage_metrics,
    "get_cache_stats": get_cache_stats,
    "get_model_costs": get_model_costs,
    "get_latency_report": get_latency_report,
    "simulate_routing_policy": simulate_routing_policy,
    "simulate_cache_threshold": simulate_cache_threshold,
    "estimate_savings": estimate_savings,
    "create_action_plan": create_action_plan,
    "request_human_approval": request_human_approval,
    "apply_local_policy": apply_local_policy,
    "write_audit_event": write_audit_event,
    "recommend_fallback_model": recommend_fallback_model,
    "recommend_cache_only": recommend_cache_only,
    "recommend_retry_policy": recommend_retry_policy,
    "create_alert": create_alert,
}


def run_tool(tool_name: str, run_id: str, input_dict: dict[str, Any], db: Any) -> dict[str, Any]:
    """Execute a tool, time it, and append an AgentToolCall row (spec shape)."""
    started = time.monotonic()
    status = "success"
    if tool_name not in TOOL_REGISTRY:
        output: dict[str, Any] = {"error": f"unknown tool: {tool_name}"}
        status = "error"
    else:
        try:
            output = TOOL_REGISTRY[tool_name](run_id, input_dict or {}, db)
        except Exception as exc:  # noqa: BLE001 - tools must never crash the run
            output = {"error": f"{type(exc).__name__}: {exc}"}
            status = "error"
    duration_ms = int((time.monotonic() - started) * 1000)

    record: dict[str, Any] = {
        "tool": tool_name,
        "input": input_dict or {},
        "output": output,
        "duration_ms": duration_ms,
        "status": status,
    }

    # Durable copy: append to the run's tool_calls JSON list.
    run = _fetch_run(db, run_id)
    if run is not None and hasattr(run, "tool_calls"):
        try:
            calls = list(run.tool_calls or [])
            calls.append(record)
            run.tool_calls = calls
            db.commit()
        except Exception:
            db.rollback()

    # Durable copy: AgentToolCall row (lazy import, guarded).
    try:
        from app.db import models

        row = models.AgentToolCall(
            run_id=run_id,
            tool=tool_name,
            input=input_dict or {},
            output=output,
            duration_ms=duration_ms,
            status=status,
            created_at=datetime.now(UTC),
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()

    return record


__all__ = ["TOOL_REGISTRY", "run_tool", "FINOPS_TOOLS", "RELIABILITY_TOOLS"]
