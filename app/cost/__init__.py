"""Cost model: pricing tables, usage tracking, and savings recommendations."""

from app.cost.pricing import (  # noqa: F401
    EXPENSIVE_MODELS,
    KNOWN_MODELS,
    MODEL_PRICING,
    cache_read_cost,
    estimate_cost,
    get_model_pricing,
    is_expensive_model,
)
from app.cost.recommendations import generate_recommendations  # noqa: F401
from app.cost.tracker import (  # noqa: F401
    get_cache_savings_total,
    get_daily_spend,
    get_model_wise_spend,
    get_monthly_spend,
    get_total_spend,
    get_usage_stats,
    record_usage,
)

__all__ = [
    "EXPENSIVE_MODELS",
    "KNOWN_MODELS",
    "MODEL_PRICING",
    "cache_read_cost",
    "estimate_cost",
    "generate_recommendations",
    "get_cache_savings_total",
    "get_daily_spend",
    "get_model_pricing",
    "get_model_wise_spend",
    "get_monthly_spend",
    "get_total_spend",
    "get_usage_stats",
    "is_expensive_model",
    "record_usage",
]
