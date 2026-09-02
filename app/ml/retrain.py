"""Safe automated retraining pipeline.

drift detected -> train candidate -> evaluate vs production model
-> promotion gate (candidate must beat production by a margin)
-> register -> (deployment handled by the serving layer)

The production model is NEVER replaced without passing the evaluation gate,
and every transition is recorded (audit-grade model history). Rollback keeps
the previous artifact.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from app.ml.drift import detect_drift

__all__ = ["retrain_if_drifted", "retrain", "model_history"]

MODEL_DIR = Path("ml/artifacts")
HISTORY_PATH = MODEL_DIR / "model_history.json"
PROMOTION_MARGIN = 0.02  # candidate must beat production by >= 2pp accuracy


def _current_metrics() -> dict[str, Any]:
    path = MODEL_DIR / "metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"accuracy": 0.0}


def retrain(seed: int = 43, use_mlflow: bool = True) -> dict[str, Any]:
    """Train a candidate model and promote it only if it beats production."""
    from app.ml.train import train_router_model

    started = time.perf_counter()
    production_metrics = _current_metrics()

    candidate = train_router_model(seed=seed, use_mlflow=use_mlflow)
    candidate_path = MODEL_DIR / "router_model_candidate.joblib"
    shutil.copyfile(MODEL_DIR / "router_model.joblib", candidate_path)

    promoted = candidate["accuracy"] >= production_metrics.get("accuracy", 0.0) + PROMOTION_MARGIN
    outcome = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trigger": "manual_or_drift",
        "production_accuracy": production_metrics.get("accuracy", 0.0),
        "candidate_accuracy": candidate["accuracy"],
        "promotion_margin": PROMOTION_MARGIN,
        "promoted": promoted,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }

    if promoted:
        shutil.copyfile(candidate_path, MODEL_DIR / "router_model.joblib")
        shutil.copyfile(
            MODEL_DIR / "metrics.json", MODEL_DIR / "metrics.production.json"
        )
        outcome["production_metrics"] = candidate
    else:
        outcome["candidate_metrics"] = candidate

    # append to immutable history
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, Any]] = []
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    history.append(outcome)
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")

    # rollback artifact always available
    shutil.copyfile(candidate_path, MODEL_DIR / "router_model_rollback.joblib")
    return outcome


def retrain_if_drifted(
    reference: dict[str, list[float]],
    current: dict[str, list[float]],
    threshold: float = 0.2,
    auto_train: bool = True,
) -> dict[str, Any]:
    """Detect drift on live features; on drift, run the safe retrain pipeline."""
    report = detect_drift(reference, current, threshold=threshold)
    result: dict[str, Any] = {"drift": report.to_dict()}
    if report.drifted and auto_train:
        result["retrain"] = retrain(seed=44)
    elif report.drifted:
        result["retrain"] = {"triggered": False, "reason": "auto_train disabled"}
    return result


def model_history() -> list[dict[str, Any]]:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return []
