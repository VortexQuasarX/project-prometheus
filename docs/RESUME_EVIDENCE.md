# Resume Evidence — VERIFIED claims only

Every claim below is backed by a command that was actually run on
2026-09-02 (Windows 11 host, Python 3.11 venv, unless stated). Evidence =
the command + the artifact/exit status. Claims marked NOT VERIFIED are
explicitly excluded from any resume use.

## Verified engineering evidence

| Claim | Evidence | How to reproduce |
|---|---|---|
| Built a production-minded Agentic AI Governance & FinOps control plane (FastAPI, 25+ endpoints, 19-table schema, Next.js 12-page dashboard) | `pytest tests/ -q` → 76 passed (now 79); repo at `project-prometheus/` | `git clone` + `pip install -r app/requirements.txt` + `pytest tests/ -q` |
| Designed count-gated Terraform (11 files, `enable_aws=false`, least-privilege IAM, Lambda/Aurora/EventBridge) | `infra/*.tf` inspection; CI validates | `cd infra && terraform validate` (needs terraform) |
| Enforced policy governance: versioned policies, audited changes, kill-switch modes, budget states with auto-escalation | `tests/test_policies.py`, `tests/test_cost.py` | run pytest |
| Human-in-the-loop agent runtime with tool-call logging and promotion gate | `tests/test_agents.py::test_finops_approval_flow` | run pytest |
| Semantic cache with measured savings | `tests/test_cache.py::test_cache_miss_then_hit` (`cost_saved_usd > 0`) | run pytest |
| Guardrails: PII masking vs blocking, zero-cost refusals, audit events | `tests/test_guardrails.py` | run pytest |
| 12-event trace timeline + SSE outbox | `tests/test_traces.py` | run pytest |
| Real OpenAI-compatible LLM + embeddings providers (retry/backoff, token accounting), env-activated | `tests/test_openai_providers.py` (8 tests, httpx.MockTransport) | run pytest |
| Load tested the API with Locust; measured the SQLite concurrency boundary (25 concurrent users → 89.97% failures from write-lock contention) | `benchmark/results_*.csv`, `docs/LOAD_TESTING.md` | `locust -f benchmark/locustfile.py --headless -u 25 -r 5 -t 60s --host http://localhost:8000` |
| Rate limiter enforced 30 req/min/key under load: 806 clean 429s, server stable | Locust run 1 (`docs/LOAD_TESTING.md`) | same |
| MLOps: trained a distilled router model (LogisticRegression), measured accuracy/precision/recall/F1, logged to MLflow | `tests/test_mlops.py::test_mlflow_run_logged`, `ml/artifacts/metrics.json` | `python -m app.ml.train` |
| PSI drift detection flags real shift, no false positive on stable data | `tests/test_mlops.py::test_drift_detection_flags_real_shift` | run pytest |
| Safe retraining with promotion gate (+2pp margin) + rollback artifact | `tests/test_mlops.py::test_safe_retraining_promotion_gate` | run pytest |
| CI: GitHub Actions green (backend ruff+pytest, frontend lint+tsc+build, both Docker images) | `gh run view 33672161439` | `gh run list --repo VortexQuasarX/project-prometheus` |
| Docker images build on clean Linux CI | CI `docker` job ✓ (runs 33672161439+) | same |

## Explicitly NOT VERIFIED (do not claim)

- AWS deployment (STS rejects stored credentials; Terraform applied only up to `validate`)
- Live Kafka broker connectivity (in-memory broker tests only)
- Live Postgres/Aurora + pgvector (code path written; no server)
- Live Redis (no server)
- PySpark pipeline execution (no JVM on host)
- Airflow scheduler execution (DAG code only)
- Kubernetes cluster deployment (manifests written; kubectl dry-run offline only)
- Real LLM token spend (no API key configured)
- Multi-worker / horizontal-scale behavior (single uvicorn worker by design)
