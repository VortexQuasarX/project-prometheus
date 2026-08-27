"""Reliability Agent: anomaly detection and recommendations.

Detects: latency spikes, LLM provider errors, cache failures, retrieval
failures, budget anomalies, repeated failures.

Writes ``budget_alerts`` rows with ``alert_type=reliability_*`` and produces
a recommendation listing fallback model / cache-only mode / retry policy
change. All DB access is lazy + guarded so the module imports standalone.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.agents.tools import run_tool


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _emit_sse(event_type: str, **payload: Any) -> None:
    try:
        from app.core import events  # type: ignore
    except Exception:
        return
    try:
        emit = getattr(events, "emit_sse", None) or getattr(events, "emit", None)
        if emit is not None:
            emit(event_type=event_type, **payload)
    except Exception:
        return


def _request_rows(db: Any) -> list[Any]:
    try:
        from app.db import models

        return db.query(models.Request).all()
    except Exception:
        return []


def _failed_rows(db: Any) -> list[Any]:
    try:
        from app.db import models

        return db.query(models.FailedRequest).all()
    except Exception:
        return []


def _detect_anomalies(db: Any) -> dict[str, Any]:
    """Compute anomaly signals from usage / trace / failure stats."""
    anomalies: dict[str, Any] = {
        "latency_spike": None,
        "provider_errors": 0,
        "cache_failures": 0,
        "retrieval_failures": 0,
        "budget_anomaly": None,
        "repeated_failures": 0,
    }

    requests = _request_rows(db)
    latencies = sorted(float(getattr(r, "latency_ms", 0.0) or 0.0) for r in requests)
    if latencies:
        n = len(latencies)
        avg = sum(latencies) / n
        p95 = latencies[int(n * 0.95) - 1] if n >= 20 else latencies[-1]
        if p95 > 0 and avg > 0 and p95 > 3 * avg:
            anomalies["latency_spike"] = {"avg_ms": round(avg, 2), "p95_ms": round(p95, 2)}
        elif p95 > 2000:
            anomalies["latency_spike"] = {"avg_ms": round(avg, 2), "p95_ms": round(p95, 2)}

    for r in requests:
        error_code = str(getattr(r, "error_code", "") or "")
        if error_code.startswith("provider"):
            anomalies["provider_errors"] += 1
        elif "cache" in error_code:
            anomalies["cache_failures"] += 1
        elif "retriev" in error_code:
            anomalies["retrieval_failures"] += 1

    failed = _failed_rows(db)
    anomalies["repeated_failures"] = len(failed)
    error_types: dict[str, int] = {}
    for f in failed:
        et = str(getattr(f, "error_type", "unknown") or "unknown")
        error_types[et] = error_types.get(et, 0) + 1
    anomalies["error_type_counts"] = error_types

    try:
        from app.governance.budget import get_budget_status

        status = get_budget_status().get("status", "normal")
        if status != "normal":
            anomalies["budget_anomaly"] = status
    except Exception:
        pass

    return anomalies


def run_reliability(run: Any, params: dict[str, Any] | None, db: Any) -> None:
    """Execute the reliability analysis for an AgentRun row."""
    params = params or {}
    anomalies = _detect_anomalies(db)
    findings = [k for k, v in anomalies.items() if v not in (None, 0, {})]

    if hasattr(run, "observations"):
        try:
            run.observations = {"anomalies": anomalies}
        except Exception:
            pass

    recommendation_lines: list[str] = []

    # Fallback model recommendation.
    fallback_out = run_tool(
        "recommend_fallback_model",
        run.run_id,
        {"model": str(params.get("model", "mock-large"))},
        db,
    ).get("output", {})
    if anomalies.get("provider_errors", 0) > 0 or anomalies.get("latency_spike"):
        fallback_model = fallback_out.get("fallback_model", "mock-small")
        recommendation_lines.append(f"fallback model: {fallback_model}")
        run_tool(
            "create_alert",
            run.run_id,
            {
                "alert_type": "reliability_provider_errors",
                "severity": "critical" if anomalies["provider_errors"] > 5 else "warning",
                "message": f"{anomalies['provider_errors']} provider errors detected",
                "metadata": {"run_id": run.run_id},
            },
            db,
        )

    # Cache-only mode recommendation.
    if anomalies.get("provider_errors", 0) > 0 or anomalies.get("latency_spike"):
        cache_only_out = run_tool(
            "recommend_cache_only",
            run.run_id,
            {"reason": "provider instability or latency spike"},
            db,
        ).get("output", {})
        recommendation_lines.append(cache_only_out.get("recommendation", "enable cache_only mode"))

    # Retry policy recommendation.
    if anomalies.get("repeated_failures", 0) > 0:
        retry_out = run_tool(
            "recommend_retry_policy",
            run.run_id,
            {"max_retries": 2, "base_backoff_seconds": 1.0},
            db,
        ).get("output", {})
        recommendation_lines.append(f"retry policy: {retry_out.get('retry_policy', {})}")

    # Budget anomaly alert.
    if anomalies.get("budget_anomaly"):
        run_tool(
            "create_alert",
            run.run_id,
            {
                "alert_type": "reliability_budget_anomaly",
                "severity": "critical" if anomalies["budget_anomaly"] == "exceeded" else "warning",
                "message": f"budget anomaly: {anomalies['budget_anomaly']}",
                "metadata": {"run_id": run.run_id},
            },
            db,
        )
        recommendation_lines.append("review budget: budget status is " + anomalies["budget_anomaly"])

    # Retrieval / cache failure alerts.
    if anomalies.get("cache_failures", 0) > 0:
        run_tool(
            "create_alert",
            run.run_id,
            {
                "alert_type": "reliability_cache_failures",
                "severity": "warning",
                "message": f"{anomalies['cache_failures']} cache failures detected",
                "metadata": {"run_id": run.run_id},
            },
            db,
        )
    if anomalies.get("retrieval_failures", 0) > 0:
        run_tool(
            "create_alert",
            run.run_id,
            {
                "alert_type": "reliability_retrieval_failures",
                "severity": "warning",
                "message": f"{anomalies['retrieval_failures']} retrieval failures detected",
                "metadata": {"run_id": run.run_id},
            },
            db,
        )

    recommendation = {
        "text": "; ".join(recommendation_lines) if recommendation_lines else "no anomalies detected",
        "anomalies": findings,
    }
    if hasattr(run, "recommendation"):
        try:
            run.recommendation = recommendation
        except Exception:
            pass

    try:
        run.status = "verified"
        run.outcome = {"anomalies": findings, "alerts_created": len(findings)}
    except Exception:
        pass

    run_tool(
        "write_audit_event",
        run.run_id,
        {
            "action": "agent.reliability.completed",
            "resource": run.run_id,
            "actor": "reliability_agent",
            "metadata": {"anomalies": findings},
        },
        db,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()


__all__ = ["run_reliability"]
