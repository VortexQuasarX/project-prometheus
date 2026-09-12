"""Model price catalog and unit-cost helpers.

Exact numbers per DECISIONS.md B11. Each entry has the four spec fields
(input/output/cache_read/cache_write) in USD per 1k tokens.
"""

from __future__ import annotations

from collections.abc import Iterable

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
    "apac.amazon.nova-micro-v1:0": {
        "input_cost_per_1k_tokens": 0.000035,
        "output_cost_per_1k_tokens": 0.000140,
        "cache_read_cost_per_1k_tokens": 0.000010,
        "cache_write_cost_per_1k_tokens": 0.000020,
    },
    "apac.amazon.nova-lite-v1:0": {
        "input_cost_per_1k_tokens": 0.000060,
        "output_cost_per_1k_tokens": 0.000240,
        "cache_read_cost_per_1k_tokens": 0.000015,
        "cache_write_cost_per_1k_tokens": 0.000030,
    },
    "apac.amazon.nova-pro-v1:0": {
        "input_cost_per_1k_tokens": 0.000800,
        "output_cost_per_1k_tokens": 0.003200,
        "cache_read_cost_per_1k_tokens": 0.000200,
        "cache_write_cost_per_1k_tokens": 0.000400,
    },
    "global.amazon.nova-2-lite-v1:0": {
        "input_cost_per_1k_tokens": 0.000060,
        "output_cost_per_1k_tokens": 0.000240,
        "cache_read_cost_per_1k_tokens": 0.000015,
        "cache_write_cost_per_1k_tokens": 0.000030,
    },
    "amazon.titan-embed-text-v2:0": {
        "input_cost_per_1k_tokens": 0.000020,
        "output_cost_per_1k_tokens": 0.0,
        "cache_read_cost_per_1k_tokens": 0.0,
        "cache_write_cost_per_1k_tokens": 0.0,
    },
    "amazon.titan-embed-image-v1": {
        "input_cost_per_1k_tokens": 0.000080,
        "output_cost_per_1k_tokens": 0.0,
        "cache_read_cost_per_1k_tokens": 0.0,
        "cache_write_cost_per_1k_tokens": 0.0,
    },
    # Meta Llama 3
    "meta.llama3-8b-instruct-v1:0": {
        "input_cost_per_1k_tokens": 0.000300,
        "output_cost_per_1k_tokens": 0.000600,
        "cache_read_cost_per_1k_tokens": 0.000075,
        "cache_write_cost_per_1k_tokens": 0.000150,
    },
    "meta.llama3-70b-instruct-v1:0": {
        "input_cost_per_1k_tokens": 0.002650,
        "output_cost_per_1k_tokens": 0.003500,
        "cache_read_cost_per_1k_tokens": 0.000660,
        "cache_write_cost_per_1k_tokens": 0.001320,
    },
    # Google Gemma 3
    "google.gemma-3-4b-it": {
        "input_cost_per_1k_tokens": 0.000080,
        "output_cost_per_1k_tokens": 0.000160,
        "cache_read_cost_per_1k_tokens": 0.000020,
        "cache_write_cost_per_1k_tokens": 0.000040,
    },
    "google.gemma-3-12b-it": {
        "input_cost_per_1k_tokens": 0.000250,
        "output_cost_per_1k_tokens": 0.000500,
        "cache_read_cost_per_1k_tokens": 0.000060,
        "cache_write_cost_per_1k_tokens": 0.000120,
    },
    "google.gemma-3-27b-it": {
        "input_cost_per_1k_tokens": 0.000550,
        "output_cost_per_1k_tokens": 0.001100,
        "cache_read_cost_per_1k_tokens": 0.000140,
        "cache_write_cost_per_1k_tokens": 0.000280,
    },
    # DeepSeek
    "deepseek.v3-v1:0": {
        "input_cost_per_1k_tokens": 0.000500,
        "output_cost_per_1k_tokens": 0.001500,
        "cache_read_cost_per_1k_tokens": 0.000125,
        "cache_write_cost_per_1k_tokens": 0.000250,
    },
    # Mistral AI
    "mistral.mistral-7b-instruct-v0:2": {
        "input_cost_per_1k_tokens": 0.000150,
        "output_cost_per_1k_tokens": 0.000200,
        "cache_read_cost_per_1k_tokens": 0.000040,
        "cache_write_cost_per_1k_tokens": 0.000080,
    },
    "mistral.mixtral-8x7b-instruct-v0:1": {
        "input_cost_per_1k_tokens": 0.000450,
        "output_cost_per_1k_tokens": 0.000700,
        "cache_read_cost_per_1k_tokens": 0.000110,
        "cache_write_cost_per_1k_tokens": 0.000220,
    },
    "mistral.mistral-large-2402-v1:0": {
        "input_cost_per_1k_tokens": 0.004000,
        "output_cost_per_1k_tokens": 0.012000,
        "cache_read_cost_per_1k_tokens": 0.001000,
        "cache_write_cost_per_1k_tokens": 0.002000,
    },
    "mistral.ministral-3-3b-instruct": {
        "input_cost_per_1k_tokens": 0.000080,
        "output_cost_per_1k_tokens": 0.000160,
        "cache_read_cost_per_1k_tokens": 0.000020,
        "cache_write_cost_per_1k_tokens": 0.000040,
    },
    "mistral.ministral-3-8b-instruct": {
        "input_cost_per_1k_tokens": 0.000150,
        "output_cost_per_1k_tokens": 0.000300,
        "cache_read_cost_per_1k_tokens": 0.000040,
        "cache_write_cost_per_1k_tokens": 0.000080,
    },
    "mistral.ministral-3-14b-instruct": {
        "input_cost_per_1k_tokens": 0.000300,
        "output_cost_per_1k_tokens": 0.000600,
        "cache_read_cost_per_1k_tokens": 0.000075,
        "cache_write_cost_per_1k_tokens": 0.000150,
    },
    # Qwen
    "qwen.qwen3-32b-v1:0": {
        "input_cost_per_1k_tokens": 0.000400,
        "output_cost_per_1k_tokens": 0.000800,
        "cache_read_cost_per_1k_tokens": 0.000100,
        "cache_write_cost_per_1k_tokens": 0.000200,
    },
    "qwen.qwen3-coder-30b-a3b-v1:0": {
        "input_cost_per_1k_tokens": 0.000400,
        "output_cost_per_1k_tokens": 0.000800,
        "cache_read_cost_per_1k_tokens": 0.000100,
        "cache_write_cost_per_1k_tokens": 0.000200,
    },
    # NVIDIA Nemotron
    "nvidia.nemotron-nano-9b-v2": {
        "input_cost_per_1k_tokens": 0.000180,
        "output_cost_per_1k_tokens": 0.000360,
        "cache_read_cost_per_1k_tokens": 0.000045,
        "cache_write_cost_per_1k_tokens": 0.000090,
    },
    # Z.AI GLM
    "zai.glm-4.7-flash": {
        "input_cost_per_1k_tokens": 0.000050,
        "output_cost_per_1k_tokens": 0.000100,
        "cache_read_cost_per_1k_tokens": 0.000012,
        "cache_write_cost_per_1k_tokens": 0.000025,
    },
}

KNOWN_MODELS: tuple[str, ...] = tuple(MODEL_PRICING)

# Default expensive set (D3/B8): policy JSON may override via expensive_models.
EXPENSIVE_MODELS: frozenset[str] = frozenset({
    "mock-large",
    "bedrock-strong",
    "apac.amazon.nova-pro-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "mistral.mistral-large-2402-v1:0",
    "google.gemma-3-27b-it",
})

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
