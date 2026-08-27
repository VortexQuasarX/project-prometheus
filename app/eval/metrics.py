"""Metrics aggregation for the evaluation harness (app/eval/metrics.py).

The SPEC's eight evaluation metrics:

    relevance, groundedness, safety, completeness, cost efficiency,
    latency, estimated cost, cacheability

Latency and estimated cost are raw quantities (ms / USD); the other six are
0..1 scores. :func:`average_metrics` computes the arithmetic mean of every
key across a list of per-case metric dicts, so the same helper serves both
the eval run summary and the ``eval_runs.avg_metrics`` JSON column.
"""

from __future__ import annotations

from typing import Any

METRIC_KEYS: tuple[str, ...] = (
    "relevance",
    "groundedness",
    "safety",
    "completeness",
    "cost_efficiency",
    "latency_ms",
    "estimated_cost_usd",
    "cacheability",
)

SCORE_KEYS: tuple[str, ...] = (
    "relevance",
    "groundedness",
    "safety",
    "completeness",
    "cost_efficiency",
    "cacheability",
)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def average_metrics(metrics_list: list[dict[str, Any]]) -> dict[str, float]:
    """Mean of the eight metric keys across ``metrics_list``.

    Missing keys are treated as 0.0 so a malformed per-case dict cannot
    break an eval run. Score keys are rounded to 4 decimals, latency to 1
    decimal (ms), estimated cost to 6 decimals (USD).
    """
    if not metrics_list:
        return {key: 0.0 for key in METRIC_KEYS}

    averages: dict[str, float] = {}
    for key in METRIC_KEYS:
        values = [float(entry.get(key, 0.0) or 0.0) for entry in metrics_list]
        averages[key] = _mean(values)

    return {
        "relevance": round(averages["relevance"], 4),
        "groundedness": round(averages["groundedness"], 4),
        "safety": round(averages["safety"], 4),
        "completeness": round(averages["completeness"], 4),
        "cost_efficiency": round(averages["cost_efficiency"], 4),
        "latency_ms": round(averages["latency_ms"], 1),
        "estimated_cost_usd": round(averages["estimated_cost_usd"], 6),
        "cacheability": round(averages["cacheability"], 4),
    }


__all__ = ["METRIC_KEYS", "SCORE_KEYS", "average_metrics"]
