"""Model price catalog and unit-cost helpers.

Exact numbers per DECISIONS.md B11. Each entry has the four spec fields
(input/output/cache_read/cache_write) in USD per 1k tokens.
"""

from __future__ import annotations

from typing import Iterable

from app.core.logging import get_logger

logger = get_logger("prometheus.pricing")

MODEL_PRICING: dict[str, dict[str, float]] = {
    "mock-small": {
        "input_cost_per_1k_tokens": 0.0050,
        "output_cost_per_1k_tokens": 0.0150,
        "cache_read_cost_per_1k_tokens": 0.0010,
        "cache_write_cost_per_1k_tokens": 0.0020,
    },
    "mock-large": {
        "input_cost_per_1k_tokens": 0.0200,
        "output_cost_per_1k_tokens": 0.0600,
        "cache_read_cost_per_1k_tokens": 0.0040,
        "cache_write_cost_per_1k_tokens": 0.0080,
    },
    "bedrock-cheap": {
        "input_cost_per_1k_tokens": 0.0030,
        "output_cost_per_1k_tokens": 0.0150,
        "cache_read_cost_per_1k_tokens": 0.0010,
        "cache_write_cost_per_1k_tokens": 0.0020,
    },
    "bedrock-strong": {
        "input_cost_per_1k_tokens": 0.0300,
        "output_cost_per_1k_tokens": 0.1500,
        "cache_read_cost_per_1k_tokens": 0.0030,
        "cache_write_cost_per_1k_tokens": 0.0060,
    },
}

KNOWN_MODELS: tuple[str, ...] = tuple(MODEL_PRICING)

# Default expensive set (D3/B8): policy JSON may override via expensive_models.
EXPENSIVE_MODELS: frozenset[str] = frozenset({"mock-large", "bedrock-strong"})

_ZERO_PRICE: dict[str, float] = {
    "input_cost_per_1k_tokens": 0.0,
    "output_cost_per_1k_tokens": 0.0,
    "cache_read_cost_per_1k_tokens": 0.0,
    "cache_write_cost_per_1k_tokens": 0.0,
}


def get_model_pricing(model: str) -> dict[str, float] | None:
    """Return the price table for a model, or None when unknown."""
    return MODEL_PRICING.get(model)


def _pricing(model: str) -> dict[str, float]:
    price = MODEL_PRICING.get(model)
    if price is None:
        logger.warning("No pricing entry for model %r; treating as $0 (check MODEL_PRICING)", model)
        return _ZERO_PRICE
    return price


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
) -> float:
    """Estimated USD cost of one request: input + output + cache-write legs (B11)."""
    price = _pricing(model)
    total = (
        input_tokens * price["input_cost_per_1k_tokens"]
        + output_tokens * price["output_cost_per_1k_tokens"]
        + cache_write_tokens * price["cache_write_cost_per_1k_tokens"]
    ) / 1000.0
    return round(total, 6)


def cache_read_cost(model: str, input_tokens: int) -> float:
    """USD cost of serving a cache hit for ``input_tokens``."""
    price = _pricing(model)
    total = input_tokens * price["cache_read_cost_per_1k_tokens"] / 1000.0
    return round(total, 6)


def is_expensive_model(model: str, expensive_models: Iterable[str] | None = None) -> bool:
    """True when the model is on the policy's expensive list (default per B8/D3)."""
    if expensive_models is not None:
        return model in set(expensive_models)
    return model in EXPENSIVE_MODELS
