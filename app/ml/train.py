"""Train the learned router model (distilled from the heuristic router).

Pipeline: build dataset -> TF-IDF-free numeric features -> LogisticRegression
-> train/test split evaluation -> joblib artifact + metrics.json -> MLflow
tracking (local ./mlruns backend) with parameters/metrics/artifacts.

The model predicts complexity_class (cheap=0 / strong=1) used by the Router
Agent to pick CHEAP_MODEL vs STRONG_MODEL.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib

from app.ml.dataset import FEATURE_NAMES, build_dataset, extract_features

__all__ = ["train_router_model", "load_router_model", "predict_complexity"]

MODEL_DIR = Path("ml/artifacts")
MLRUNS_DIR = Path("ml/mlruns")


def train_router_model(
    *,
    test_size: float = 0.25,
    seed: int = 42,
    use_mlflow: bool = True,
) -> dict[str, Any]:
    """Train, evaluate, persist and (optionally) register the routing model.

    Returns a metrics dict — every number in it is measured, not assumed.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    from sklearn.model_selection import train_test_split

    dataset = build_dataset(seed=seed)
    X = [[row[f] for f in FEATURE_NAMES] for row in dataset.features]
    y = dataset.labels

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    started = time.perf_counter()
    model = LogisticRegression(max_iter=1000, random_state=seed)
    model.fit(X_train, y_train)
    train_seconds = round(time.perf_counter() - started, 4)

    y_pred = model.predict(X_test)
    metrics = {
        "rows": len(dataset),
        "train_rows": len(y_train),
        "test_rows": len(y_test),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "train_seconds": train_seconds,
        "feature_names": FEATURE_NAMES,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "router_model.joblib"
    joblib.dump(model, model_path)
    metrics["artifact"] = str(model_path)
    metrics["model_size_bytes"] = model_path.stat().st_size
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if use_mlflow:
        try:
            import mlflow

            mlflow.set_tracking_uri(f"sqlite:///{(Path.cwd() / MLRUNS_DIR).resolve() / 'mlflow.db'}")
            mlflow.set_experiment("prometheus-router")
            with mlflow.start_run(run_name="router-distillation"):
                mlflow.log_params(
                    {"test_size": test_size, "seed": seed, "model": "LogisticRegression",
                     "features": len(FEATURE_NAMES), "rows": len(dataset)}
                )
                mlflow.log_metrics(
                    {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
                )
                mlflow.log_artifact(str(model_path), artifact_path="model")
                mlflow.log_artifact(str(MODEL_DIR / "metrics.json"), artifact_path="metrics")
            metrics["mlflow_run"] = True
        except Exception as exc:  # MLflow must never break training
            metrics["mlflow_run"] = False
            metrics["mlflow_error"] = str(exc)[:200]

    return metrics


def load_router_model(model_path: Path | None = None) -> Any:
    """Load the trained routing model (used by the inference service)."""
    path = model_path or (Path("ml/artifacts") / "router_model.joblib")
    if not path.exists():
        raise FileNotFoundError(
            f"router model not found at {path}; run `python -m app.ml.train` first"
        )
    return joblib.load(path)


def predict_complexity(model: Any, text: str) -> dict[str, Any]:
    """Predict complexity class for one query using the trained model."""
    features = extract_features(text)
    X = [[features[f] for f in FEATURE_NAMES]]
    prediction = int(model.predict(X)[0])
    confidence = max(model.predict_proba(X)[0])
    return {
        "complexity_class": "strong" if prediction == 1 else "cheap",
        "confidence": round(float(confidence), 4),
        "features": features,
    }


if __name__ == "__main__":
    result = train_router_model()
    print(json.dumps(result, indent=2))
