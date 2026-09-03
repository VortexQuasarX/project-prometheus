# Benchmarks (measured only)

All numbers on this page were **measured on this machine** with the commands
shown. Nothing is estimated. Environment: Windows 11 host, Python 3.11 venv,
SQLite WAL, mock LLM provider, single uvicorn worker (unless stated).

## API latency — single user (Locust, light load)

Measured via `benchmark/locustfile.py` light runs and the boot smoke
(`GET /api/v1/health` ~1-5 ms, `POST /api/v1/chat` pipeline ~300-900 ms
including guardrails + router + RAG + mock LLM + evaluator + 12 trace writes).
See `docs/LOAD_TESTING.md` for the load profile.

## Concurrency boundary (VERIFIED — reproduced twice)

| Users (concurrent) | Failure rate | Cause |
|---|---|---|
| sequential / 1 user | 0% | baseline |
| 25 users | 89.97% (834/927) | SQLite single-writer lock contention → HTTP 500 |

Evidence: `benchmark/results_stats.csv`, `results_failures.csv`,
`results_stats_history.csv` (run 2, 60s, 25 users). Full write-up:
`docs/LOAD_TESTING.md`.

**Fix path:** PostgreSQL/Aurora (V2) — the data layer is SQLAlchemy-portable
and `DATABASE_URL`-driven by design.

## Rate limiting under load (VERIFIED)

Run 1 (default 30 req/min/key): 806 clean `429 Too Many Requests` served with
`Retry-After` headers — the governance limiter enforced policy under load
without dropping the server.

## Model training (MLOps, measured)

`python -m app.ml.train` on the distilled router dataset (48 rows):

- accuracy/precision/recall/F1 recorded in `ml/artifacts/metrics.json`
- MLflow run recorded (sqlite backend, experiment `prometheus-router`)
- train time + model size recorded in the same metrics file

Reproduce: `python -m app.ml.train`

## ML inference service (VERIFIED via TestClient/live)

`ml_service/main.py` — `/health`, `/ready`, `/predict`, `/predict/batch`,
`/metrics`, `/version`; per-class prediction counters and latency histogram.
Benchmark harness: `benchmark/locustfile.py` pointed at `:8100`.

## ML inference LIVE benchmark + gRPC contract (VERIFIED 2026-09-03)

Live run against uvicorn on 127.0.0.1:8100 (router_model.joblib trained artifact):

- Load: Locust headless, 20 users, 30s (benchmark/locustfile_ml.py)
- **1,802 requests, 0 failures (0.00%)**
- Throughput: **61.62 req/s** aggregate (predict/simple 29.6, predict/batch 21.9, predict/complex 10.2)
- Latency: median 5ms, p90 9ms, p95 10ms, p98 15ms, p99 76ms, max 76ms

gRPC contract (ml_service/grpc_server.py + proto/inference.proto): real socket
round-trip on 127.0.0.1:50051 via inference_pb2 stubs - Predict and
PredictBatch verified (proto serialization + servicer logic + model load).

Reproduce: train via `python -c "from app.ml.train import train_router_model; train_router_model()"`,
serve via `python -m uvicorn ml_service.main:app --port 8100`, load via
`locust -f benchmark/locustfile_ml.py -u 20 -t 30s --host http://127.0.0.1:8100`
