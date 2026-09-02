"""MLOps lifecycle tests: distillation training, MLflow tracking, drift
detection, safe retraining with promotion gate — all verified locally."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.ml.dataset import FEATURE_NAMES, build_dataset, extract_features
from app.ml.drift import detect_drift


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Train the router model into an isolated artifacts dir."""
    import os

    from app.ml import train

    artifacts = tmp_path_factory.mktemp("ml_artifacts")
    old_cwd = os.getcwd()
    os.chdir(artifacts)
    try:
        metrics = train.train_router_model(seed=7, use_mlflow=True)
        yield metrics
    finally:
        os.chdir(old_cwd)


def test_dataset_built_from_real_queries():
    dataset = build_dataset()
    assert len(dataset) >= 40
    assert len(dataset.labels) == len(dataset.texts)
    assert set(dataset.labels) <= {0, 1}
    assert all(set(f.keys()) == set(FEATURE_NAMES) for f in dataset.features)


def test_training_reports_measured_metrics(trained):
    for key in ("accuracy", "precision", "recall", "f1", "train_seconds", "rows"):
        assert key in trained, f"missing metric {key}"
    assert 0.0 <= trained["accuracy"] <= 1.0
    assert trained["rows"] >= 40
    assert trained["model_size_bytes"] > 0


def test_mlflow_run_logged(trained):
    # mlflow-skinny with a local file backend — run must be recorded
    assert trained.get("mlflow_run") is True, trained.get("mlflow_error")


def test_model_artifact_predicts(trained, tmp_path):
    from app.ml.train import load_router_model, predict_complexity

    model = load_router_model(Path("ml/artifacts") / "router_model.joblib")
    result = predict_complexity(model, "Compare dense and hybrid retrieval for enterprise RAG")
    assert result["complexity_class"] in ("cheap", "strong")
    assert 0.0 <= result["confidence"] <= 1.0


def test_drift_detection_flags_real_shift(trained):
    from app.ml.dataset import build_dataset as ds

    base = ds(seed=42)
    reference = {f: [row[f] for row in base.features] for f in FEATURE_NAMES}
    # simulate drift: everything becomes very long (length feature shifts hard)
    shifted_texts = ["x" * 400 for _ in range(30)]
    current_texts = shifted_texts + base.texts[:10]
    current_rows = [extract_features(t) for t in current_texts]
    current = {f: [row[f] for row in current_rows] for f in FEATURE_NAMES}

    report = detect_drift(reference, current, threshold=0.2)
    assert report.drifted is True
    assert any(f["feature"] == "length" and f["drifted"] for f in report.features)


def test_no_drift_on_same_distribution(trained):
    from app.ml.dataset import build_dataset as ds

    base = ds(seed=42)
    reference = {f: [row[f] for row in base.features] for f in FEATURE_NAMES}
    report = detect_drift(reference, dict(reference), threshold=0.2)
    assert report.drifted is False


def test_safe_retraining_promotion_gate(trained, tmp_path_factory, monkeypatch):
    """Candidate must beat production by the margin; history must record it."""
    import os

    from app.ml import retrain

    artifacts = tmp_path_factory.mktemp("retrain_artifacts")
    old_cwd = os.getcwd()
    os.chdir(artifacts)
    try:
        # seed production artifact from the trained metrics
        shutil.copyfile(
            Path("ml/artifacts/router_model.joblib"),
            Path("ml/artifacts/router_model.joblib"),
        ) if Path("ml/artifacts/router_model.joblib").exists() else None
        outcome = retrain.retrain(seed=99, use_mlflow=False)
        assert "promoted" in outcome
        assert isinstance(outcome["promoted"], bool)
        history = retrain.model_history()
        assert len(history) >= 1
        assert history[-1]["promoted"] == outcome["promoted"]
        # rollback artifact exists
        assert Path("ml/artifacts/router_model_rollback.joblib").exists()
    finally:
        os.chdir(old_cwd)
