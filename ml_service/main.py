"""ML inference microservice — independently deployable router model server.

Serves the trained Prometheus routing model:
- GET  /health      liveness
- GET  /ready       readiness (model loaded)
- POST /predict     single prediction
- POST /predict/batch  batched predictions
- GET  /metrics     Prometheus metrics
- GET  /version     model version + build info

Run: uvicorn ml_service.main:app --port 8100 (from repo root)
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

logger = logging.getLogger("ml_service")

MODEL_PATH = Path("ml/artifacts/router_model.joblib")

app = FastAPI(title="Prometheus ML Inference", version="1.0.0")

MODEL_VERSION = "router-1.0.0"
_model: Any = None
_loaded_at: float = 0.0

PREDICTIONS = Counter(
    "ml_predictions_total", "Total predictions", ["complexity_class"]
)
LATENCY = Histogram(
    "ml_prediction_latency_seconds",
    "Prediction latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
)
MODEL_LOADED = Gauge("ml_model_loaded", "1 when a model artifact is loaded")
LOAD_TIME = Gauge("ml_model_load_seconds", "Model load time")


class PredictRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class BatchPredictRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=64)


def load_model() -> Any:
    """Load the trained router model artifact."""
    global _model, _loaded_at
    started = time.perf_counter()
    import joblib

    _model = joblib.load(MODEL_PATH)
    _loaded_at = time.perf_counter()
    LOAD_TIME.set(_loaded_at - started)
    MODEL_LOADED.set(1)
    logger.info("model %s loaded in %.3fs", MODEL_VERSION, _loaded_at - started)
    return _model


@app.on_event("startup")
def startup() -> None:
    try:
        load_model()
    except FileNotFoundError:
        logger.warning("model artifact missing; /predict will 503 until trained")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ml-inference"}


@app.get("/ready")
def ready() -> dict:
    if _model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready", "model_version": MODEL_VERSION}


@app.get("/version")
def version() -> dict:
    return {"model_version": MODEL_VERSION, "loaded_at": _loaded_at}


@app.get("/metrics")
def metrics() -> Any:
    from prometheus_client import generate_latest

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


from fastapi import Response  # noqa: E402


@app.post("/predict")
def predict(body: PredictRequest) -> dict:
    if _model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    started = time.perf_counter()
    from app.ml.train import predict_complexity

    result = predict_complexity(_model, body.text)
    latency = time.perf_counter() - started
    PREDICTIONS.labels(complexity_class=result["complexity_class"]).inc()
    LATENCY.observe(latency)
    result["latency_ms"] = round(latency * 1000, 3)
    result["model_version"] = MODEL_VERSION
    return result


@app.post("/predict/batch")
def predict_batch(body: BatchPredictRequest) -> dict:
    if _model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    from app.ml.train import predict_complexity

    started = time.perf_counter()
    results = [predict_complexity(_model, t) for t in body.texts]
    latency = round((time.perf_counter() - started) * 1000, 3)
    for r in results:
        PREDICTIONS.labels(complexity_class=r["complexity_class"]).inc()
    return {"predictions": results, "batch_size": len(body.texts), "latency_ms": latency}
