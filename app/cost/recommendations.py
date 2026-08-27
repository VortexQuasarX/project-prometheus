"""Rule-based FinOps recommendations, derived from usage stats.

Recommendations share the exact shape of FinOps agent actions:
``{action_id, title, expected_monthly_saving_usd, risk_level, latency_impact,
approval_required, status}``. ``status`` is always ``"pending"`` — promoting a
recommendation to an ``agent_actions`` row (pending human approval) is the
FinOps agent's job.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.logging import get_logger
from app.cost.pricing import is_expensive_model
from app.cost.tracker import get_daily_spend, get_model_wise_spend, get_usage_stats
from app.db.models import CacheEntry
from app.db.session import SessionLocal

logger = get_logger("prometheus.recommendations")


def _cache_hit_count() -> int:
    with SessionLocal() as session:
        total = session.scalar(select(func.coalesce(func.sum(CacheEntry.hit_count), 0)))
        return int(total or 0)


def generate_recommendations() -> list[dict[str, Any]]:
    """Generate savings recommendations from usage stats and cache behaviour."""
    stats = get_usage_stats(days=7)
    model_wise = get_model_wise_spend()
    recs: list[dict[str, Any]] = []
    counter = 0

    def make(title: str, saving: float, risk: str, latency: str) -> dict[str, Any]:
        nonlocal counter
        counter += 1
        return {
            "action_id": f"rec_{counter:02d}",
            "title": title,
            "expected_monthly_saving_usd": round(max(0.0, saving), 2),
            "risk_level": risk,
            "latency_impact": latency,
            "approval_required": True,
            "status": "pending",
        }

    days = max(1, stats["days"])
    total_cost = stats["total_cost_usd"]

    # Rule 1 — expensive models carrying cheap-eligible traffic (D3/B8).
    expensive_cost = sum(item["cost_usd"] for item in model_wise if is_expensive_model(item["model"]))
    if expensive_cost >= 0.25:
        monthly = expensive_cost * 30.0 / days
        recs.append(make("Route simple queries to cheaper models", monthly * 0.6, "low", "minimal"))

    # Rule 2 — low cache hit rate: repeated queries pay full price.
    records = stats["usage_record_count"]
    if records >= 10:
        hit_rate = _cache_hit_count() / records
        if hit_rate < 0.30:
            recs.append(
                make("Increase cache reuse (lower similarity threshold / raise TTL)", total_cost * 0.35, "medium", "none")
            )

    # Rule 3 — spend trending near the daily budget.
    today_spend = get_daily_spend()
    if settings.daily_budget_usd > 0 and today_spend >= settings.daily_budget_usd * settings.budget_warning_ratio:
        recs.append(make("Tighten daily budget or review expensive-model usage", today_spend * 0.5, "medium", "minimal"))

    # Rule 4 — baseline cache optimisation when nothing else fires.
    if not recs:
        recs.append(make("Enable semantic caching for repeated queries", total_cost * 0.25, "low", "none"))

    return recs
