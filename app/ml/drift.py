"""Drift detection: Population Stability Index (PSI) on feature distributions.

PSI per feature between a reference window (training data) and a current
window (live traffic). PSI > threshold => drift alert + optional retrain
trigger. Fully computed from real data — no synthetic numbers.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

__all__ = ["psi", "detect_drift", "DriftReport"]


@dataclass
class DriftReport:
    drifted: bool
    threshold: float
    features: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "drifted": self.drifted,
            "threshold": self.threshold,
            "features": self.features,
            "drifted_features": [f["feature"] for f in self.features if f["drifted"]],
        }


def _quantile_bins(values: list[float], bins: int = 10) -> list[float]:
    """Equal-frequency bin edges from reference data."""
    if not values:
        return []
    sorted_vals = sorted(values)
    edges = [sorted_vals[0]]
    for i in range(1, bins):
        idx = int(i * (len(sorted_vals) - 1) / bins)
        edges.append(sorted_vals[idx])
    edges.append(sorted_vals[-1] + 1e-9)
    return sorted(set(edges))


def _psi_single(reference: list[float], current: list[float], bins: int = 10) -> float:
    """PSI between two numeric samples (10 equal-frequency reference bins)."""
    if not reference or not current:
        return 0.0
    edges = _quantile_bins(reference, bins)
    if len(edges) < 2:
        return 0.0

    def counts(sample: list[float]) -> list[float]:
        out = [0.0] * (len(edges) - 1)
        for v in sample:
            for b in range(len(edges) - 1):
                if edges[b] <= v < edges[b + 1] or (b == len(edges) - 2 and v >= edges[b + 1]):
                    out[b] += 1
                    break
        total = sum(out) or 1.0
        return [c / total for c in out]

    ref_p = counts(reference)
    cur_p = counts(current)
    psi = 0.0
    for r, c in zip(ref_p, cur_p, strict=False):
        r = max(r, 1e-6)
        c = max(c, 1e-6)
        psi += (c - r) * math.log(c / r)
    return round(psi, 6)


def psi(reference: dict[str, list[float]], current: dict[str, list[float]]) -> dict[str, float]:
    """Per-feature PSI between reference and current feature dicts."""
    out: dict[str, float] = {}
    for feature in reference:
        if feature in current:
            out[feature] = _psi_single(reference[feature], current[feature])
    return out


def detect_drift(
    reference: dict[str, list[float]],
    current: dict[str, list[float]],
    threshold: float = 0.2,
) -> DriftReport:
    """Detect feature drift; threshold follows the standard PSI convention
    (<0.1 stable, 0.1-0.25 moderate, >0.25 significant) — default 0.2."""
    per_feature = []
    drifted = False
    for feature, score in sorted(psi(reference, current).items()):
        is_drift = score > threshold
        drifted = drifted or is_drift
        per_feature.append(
            {"feature": feature, "psi": score, "drifted": is_drift}
        )
    return DriftReport(drifted=drifted, threshold=threshold, features=per_feature)
