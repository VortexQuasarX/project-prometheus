# Status — VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED / FUTURE

Last audit: 2026-09-02. Every row maps to a command in `docs/BENCHMARKS.md`,
`docs/LOAD_TESTING.md`, or `pytest tests/ -q`.

| Capability | Status | Evidence |
|---|---|---|
| FastAPI control plane, 25+ endpoints, RBAC (6 roles), multi-tenancy isolation | VERIFIED | 79/79 tests incl. matrix + cross-tenant 404 |
| Chat pipeline (guardrails → router → cache → RAG → LLM → evaluator → cost) | VERIFIED | tests/test_chat, test_traces (12 events) |
| Semantic cache (distill, savings, TTL, versioned invalidation) | VERIFIED | tests/test_cache |
| Agent runtime + human approval gate | VERIFIED | tests/test_agents |
| MLOps: distillation training, MLflow, PSI drift, safe retraining | VERIFIED (local) | tests/test_mlops |
| Real OpenAI-compatible providers (LLM + embeddings) | VERIFIED (logic, MockTransport) / live call NOT VERIFIED (no key) | tests/test_openai_providers |
| Observability: Prometheus /metrics + OTel spans | VERIFIED (local) | tests/test_observability |
| Load boundary: SQLite single-writer at 25 concurrent users | VERIFIED (measured 89.97% failures) | docs/LOAD_TESTING.md, benchmark/results_*.csv |
| Rate limiter under load | VERIFIED (806 clean 429s) | docs/LOAD_TESTING.md |
| GitHub CI (ruff, pytest, frontend, docker images) | VERIFIED | run 33672161439 ✓ |
| Terraform (11 files, cost-gated) | PARTIALLY VERIFIED (validate-by-inspection; CI validate pending terraform binary) | infra/*.tf |
| Docker images | VERIFIED on CI build; local compose run NOT VERIFIED (daemon down) | ci.yml |
| AWS deployment | NOT VERIFIED (STS rejects stored keys) | — |
| Kafka live broker | NOT VERIFIED (pipeline logic VERIFIED via in-memory broker) | tests/test_events_pipeline |
| PySpark execution | NOT VERIFIED (no JVM; pipeline code shipped) | app/spark/ (if present) |
| Airflow scheduler | NOT VERIFIED (Windows; DAG code shipped) | app/airflow_dags/ |
| K8s cluster deploy | NOT VERIFIED (manifests + kubectl dry-run only) | infra/k8s/ |
| SSO/OIDC, full RBAC UI, Postgres live, Redis live, multi-worker scale | FUTURE (docs/ROADMAP.md V2/V3) | — |
