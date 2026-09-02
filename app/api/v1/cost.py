"""GET /api/v1/cost-report — spend rollups + savings + recommendations."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.rbac import require_permission
from app.cost.recommendations import generate_recommendations
from app.cost.tracker import (
    get_cache_savings_total,
    get_daily_spend,
    get_model_wise_spend,
    get_monthly_spend,
    get_total_spend,
    get_usage_stats,
)

router = APIRouter()


@router.get("/cost-report")
def cost_report(_: object = Depends(require_permission("cost:read"))) -> dict:
    """Daily/monthly/model-wise spend, cache savings and recommendations."""
    stats = get_usage_stats(days=7)
    today = datetime.now(UTC).date().isoformat()
    month = today[:7]
    return {
        "daily": [{"date": today, "cost": get_daily_spend()}],
        "monthly": [{"month": month, "cost": get_monthly_spend()}],
        "model_wise": get_model_wise_spend(),
        "total_spend_usd": get_total_spend(),
        "cache_savings_usd": get_cache_savings_total(),
        "recommendations": generate_recommendations(),
        "trend": stats.get("daily_series", []),
    }
