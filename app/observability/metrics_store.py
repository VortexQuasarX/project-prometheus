"""Dashboard metrics aggregation (GET /api/v1/metrics payload, Section 2)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.cost.recommendations import generate_recommendations
from app.cost.tracker import get_daily_spend, get_model_wise_spend
from app.db.models import (
    AgentAction,
    BudgetAlert,
    FailedRequest,
    Policy,
    Request,
    UsageRecord,
    ensure_utc,
    iso_utc,
    utcnow,
)
from app.db.session import SessionLocal


def _active_policy(session: Any) -> dict[str, Any] | None:
    row = session.scalar(
        select(Policy).where(Policy.is_active.is_(True)).order_by(Policy.policy_version.desc())
    )
    return dict(row.body) if row is not None else None


def _budget_status(daily_spend: float, budget_usd: float) -> str:
    """normal (<70%) / warning (70-90%) / critical (90-100%) / exceeded (>=100%)."""
    if budget_usd <= 0:
        return "normal"
    ratio = daily_spend / budget_usd
    if ratio >= 1.0:
        return "exceeded"
    if ratio >= settings.budget_critical_ratio:
        return "critical"
    if ratio >= settings.budget_warning_ratio:
        return "warning"
    return "normal"


def _hour_key(value: Any) -> str:
    return ensure_utc(value).replace(minute=0, second=0, microsecond=0).isoformat()


def _requests_last_24h(session: Any) -> list[dict[str, Any]]:
    cutoff = utcnow() - timedelta(hours=24)
    buckets: dict[str, dict[str, Any]] = {}
    now = utcnow()
    for offset in range(24):
        hour = now - timedelta(hours=23 - offset)
        key = hour.replace(minute=0, second=0, microsecond=0).isoformat()
        buckets[key] = {"hour": key, "requests": 0, "cost_usd": 0.0}

    request_times = session.scalars(select(Request.created_at).where(Request.created_at >= cutoff)).all()
    for timestamp in request_times:
        key = _hour_key(timestamp)
        if key in buckets:
            buckets[key]["requests"] += 1

    cost_rows = session.execute(
        select(UsageRecord.created_at, UsageRecord.cost_usd).where(UsageRecord.created_at >= cutoff)
    ).all()
    for timestamp, cost in cost_rows:
        key = _hour_key(timestamp)
        if key in buckets:
            buckets[key]["cost_usd"] = round(buckets[key]["cost_usd"] + float(cost or 0.0), 6)

    return [buckets[key] for key in sorted(buckets)]


def get_metrics() -> dict[str, Any]:
    """Aggregate dashboard counters (shape per subagent_01.md Section 2)."""
    with SessionLocal() as session:
        total_requests = int(session.scalar(select(func.count(Request.id))) or 0)
        cache_hits = int(
            session.scalar(select(func.count(Request.id)).where(Request.cache_hit.is_(True))) or 0
        )
        total_cost = float(
            session.scalar(select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0))) or 0.0
        )
        avg_latency = float(session.scalar(select(func.avg(Request.latency_ms))) or 0.0)
        failed_requests = int(session.scalar(select(func.count(FailedRequest.id))) or 0)
        pending_approvals = int(
            session.scalar(
                select(func.count(AgentAction.id)).where(AgentAction.status == "pending")
            )
            or 0
        )
        alert_rows = session.scalars(select(BudgetAlert).order_by(BudgetAlert.id.desc()).limit(5)).all()
        policy = _active_policy(session)
        requests_24h = _requests_last_24h(session)

    cache_hit_rate = round(cache_hits / total_requests, 4) if total_requests else 0.0
    daily_spend = get_daily_spend()
    budget_usd = float(policy.get("daily_budget_usd", settings.daily_budget_usd)) if policy else settings.daily_budget_usd

    recent_alerts = [
        {
            "id": row.id,
            "alert_type": row.alert_type,
            "severity": row.severity,
            "message": row.message,
            "metadata": row.details or {},
            "created_at": iso_utc(row.created_at),
        }
        for row in alert_rows
    ]

    return {
        "total_requests": total_requests,
        "total_cost_usd": round(total_cost, 6),
        "cache_hit_rate": cache_hit_rate,
        "avg_latency_ms": round(avg_latency, 1),
        "budget_status": _budget_status(daily_spend, budget_usd),
        "kill_switch_mode": str(policy.get("kill_switch_mode", "off")) if policy else "off",
        "recent_alerts": recent_alerts,
        "pending_approvals": pending_approvals,
        "top_recommendations": generate_recommendations()[:3],
        "requests_last_24h": requests_24h,
        "failed_requests": failed_requests,
        "model_usage": get_model_wise_spend(),
    }
