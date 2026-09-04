# Status — VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED / FUTURE

Superseded for enterprise continuation: **`docs/ENTERPRISE_BUILD_STATUS.md`**
(audit 2026-09-04, git `5858e00`). This table is retained as a historical
snapshot from 2026-09-02. Where it conflicts with the 2026-09-04 audit
(especially Postgres+Redis load “100% success” and AWS STS rejection),
treat the later audit as authoritative.

Last snapshot: 2026-09-02. Every row was intended to map to a command in
`docs/BENCHMARKS.md`, `docs/LOAD_TESTING.md`, or `pytest tests/ -q`.

| Capability | Status | Evidence |
|---|---|---|
| FastAPI control plane, 25+ endpoints, RBAC (6 roles), multi-tenancy isolation | VERIFIED | 79/79 tests incl. matrix + cross-tenant 404 |
| Chat pipeline (guardrails → router → cache → RAG → LLM → evaluator → cost) | VERIFIED | tests/test_chat, test_traces (12 events) |
| Semantic cache (distill, savings, TTL, versioned invalidation) | VERIFIED | tests/test_cache |
| Agent runtime + human approval gate | VERIFIED | tests/test_agents |
| MLOps: distillation training, MLflow, PSI drift, safe retraining | VERIFIED (local) | tests/test_mlops |
| Real OpenAI-compatible providers (LLM + embeddings) | VERIFIED (logic, MockTransport) / live call NOT VERIFIED (no key) | tests/test_openai_providers |
| Observability: Prometheus /metrics + OTel spans | VERIFIED (local) | tests/test_observability |
| Load boundary: SQLite single-writer at 25 concurrent users | VERIFIED (measured 89.97% failures) - SUPERCEDED | docs/LOAD_TESTING.md |
| Load boundary: Postgres+Redis at 25 concurrent users | VERIFIED (100% success, 0.00% failures) | docs/LOAD_TESTING.md |
| Rate limiter under load | VERIFIED (clean 429s) | docs/LOAD_TESTING.md |
| GitHub CI (ruff, pytest, frontend, docker images) | VERIFIED | run 33672161439 ✓ |
| Terraform (11 files, cost-gated) | PARTIALLY VERIFIED (validate-by-inspection; CI validate pending terraform binary) | infra/*.tf |
| Docker images | VERIFIED on CI build; local compose VERIFIED (Postgres, Redis, API) | ci.yml |
| AWS deployment | NOT VERIFIED (STS rejects stored keys) | — |
| Kafka live broker | NOT VERIFIED (pipeline logic VERIFIED via in-memory broker) | tests/test_events_pipeline |
| PySpark execution | NOT VERIFIED (no JVM; pipeline code shipped) | app/spark/ (if present) |
| Airflow scheduler | NOT VERIFIED (Windows; DAG code shipped) | app/airflow_dags/ |
| K8s cluster deploy | NOT VERIFIED (manifests + kubectl dry-run only) | infra/k8s/ |
| SSO/OIDC, full RBAC UI, multi-worker scale | FUTURE (docs/ROADMAP.md V2/V3) | — |
