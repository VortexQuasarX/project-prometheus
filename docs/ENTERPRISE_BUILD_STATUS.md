# Enterprise Build Status — Phase 0 Audit

**Audit date:** 2026-09-04  
**Git HEAD:** `5858e00` (`main`, clean, tracking `origin/main`)  
**AWS profile:** `prometheus` · **region:** `ap-south-1`  
**Honesty labels:** VERIFIED / PARTIALLY VERIFIED / CODE-READY / NOT VERIFIED / BLOCKED

No AWS resources were created in this phase.

## 1. Report reconciliation (latest verified result wins)

| Source | Date / HEAD | How to treat it |
|---|---|---|
| `docs/PROJECT_HANDOFF.md` | 2026-09-03, written against `7eccddc` | Stale on test count, Redis/Postgres *code*, ML live benchmark, compose services. Architecture narrative still useful. |
| `docs/STATUS.md` | 2026-09-02 | Stale. The row “Postgres+Redis 25cw → 100% success” is **not** backed by `docs/BENCHMARKS.md` or CSVs in this clone. Treat as overclaim until re-measured. |
| `docs/RESUME_EVIDENCE.md` | 2026-09-02 | Stale (76/79 tests; AWS STS rejected). Keep claims only where re-verified below. |
| `docs/BENCHMARKS.md` | updated through `5858e00` | **Authoritative for ML live numbers.** API load numbers remain SQLite-era. |
| Git `fba6cb0` + `5858e00` | 2026-09-03 | **Authoritative for current code:** Redis Lua limiter, Postgres pool + FK-safe request rows, usage_records index, compose Postgres/Redis, ML gRPC + live Locust, extra k8s objects. |

**Reconciliation rule used:** git HEAD + commands run on 2026-09-04 beat older markdown.

## 2. Commands run this audit (this machine)

| Check | Result |
|---|---|
| `git status` / `git log` | Clean `main` at `5858e00` |
| `pytest tests/` | **89 collected, 89 passed** (ruff-clean suite). `test_spark_pipeline` **not collected** (pyspark not installed). |
| `ruff check app tests scripts` | All checks passed |
| `web`: `npm run lint` | exit 0 |
| `web`: `npm run type-check` | exit 0 |
| `web`: `npm run build` | Next.js 14.2.35, 13 routes, exit 0 |
| Docker daemon | **DOWN** (`com.docker.service` Stopped; npipe to Docker Desktop missing) |
| PostgreSQL / Redis ports | **Nothing listening** on 5432 / 6379 |
| Java / Spark JVM | **Not installed** |
| Terraform CLI | **Not on PATH** |
| `kubectl` client | v1.36.1 present |
| Kubernetes API | **No cluster** (`localhost:8080` refused). Client dry-run cannot validate without a server. |
| `aws sts get-caller-identity --profile prometheus` | Succeeds. Identity is **account ROOT** (`arn:aws:iam::481154548615:root`). Region `ap-south-1`. |

## 3. Capability matrix (current, honest)

### VERIFIED (re-run or measured artifact on this clone)

| Capability | Evidence |
|---|---|
| FastAPI control plane | 89/89 pytest; 25 HTTP handlers under `/api/v1` + `GET /metrics` |
| Frontend (12 pages) | eslint + tsc + `next build` green |
| RBAC 6 roles + 19 permissions | `app/core/rbac.py` + `tests/test_rbac.py` (9 tests) |
| Multi-tenancy / isolation | `test_cross_tenant_isolation` in suite |
| Chat pipeline (heuristic router) | `tests/test_chat.py`; `router_decide()` in `app/api/v1/chat.py` |
| Semantic cache (SQL-backed) | `tests/test_cache.py` |
| Guardrails, policies, kill switch, budgets | policy/cost/guardrail tests |
| Agent runtime + FinOps approval | `tests/test_agents.py` |
| Audit append-only | chat/policy tests |
| Eval harness | `tests/test_evals.py` |
| Observability (in-process Prom + OTel) | `tests/test_observability.py` |
| Alembic on SQLite | `tests/test_alembic.py` (2 revisions: `16695cabd80f` → `048fa8e0c0dc`) |
| OpenAI-compatible providers (MockTransport) | 8 tests |
| MLOps train / MLflow / PSI / retrain gate | `tests/test_mlops.py` |
| ML inference HTTP (TestClient) | `tests/test_ml_service.py` |
| ML inference **live** HTTP load (prior session, recorded) | `docs/BENCHMARKS.md`: 1802 req / 30s, 0 fail, 61.62 rps, p95 10ms |
| Event pipeline **semantics** (in-memory broker) | `tests/test_events_pipeline.py` (3) |
| Airflow DAG **structure** (stubbed import) | `tests/test_airflow_dag.py` (4) — not a scheduler run |
| CI design | `.github/workflows/ci.yml` (ruff, pytest, bandit, pip-audit, frontend, docker builds). Live GitHub run not re-queried this session. |

### PARTIALLY VERIFIED

| Capability | What is real | What is not |
|---|---|---|
| PostgreSQL production path | Pool (`pool_size=10`, overflow 20, recycle 1800, `pool_pre_ping`), FK-safe request insert, compose service, `psycopg2-binary`, Alembic index migration | **No live Postgres** this audit. Alembic/EXPLAIN/concurrency **not** re-measured on PG. |
| Redis rate limiter | Atomic Lua sliding window + in-memory fallback in `app/core/middleware.py` | **No live Redis**. Lua path, concurrent workers, fallback under Redis death **not** re-measured. |
| Semantic / cache Redis | `CACHE_PROVIDER` / `REDIS_URL` exist | Cache remains SQL/local; Redis is **rate-limit only**. |
| ML gRPC | `ml_service/grpc_server.py` + proto; BENCHMARKS claims socket round-trip on 2026-09-03 | **Not re-run** this session (ports 8100/50051 idle). |
| Kubernetes manifests | YAML present: namespace, API, ML, HPA 2→10 @70% CPU, NetworkPolicy, ConfigMap/Secret placeholders, Ingress | **No cluster**. Probes/HPA/rollback **NOT VERIFIED**. |
| Terraform | 11 modules, `enable_aws=false`, NAT off, Lambda+APIGW+ECR, Aurora SV2, S3, IAM, EventBridge, CloudWatch | `terraform` binary missing; plan/apply **NOT VERIFIED**. Region default in TF is `us-east-1`, CLI profile is `ap-south-1`. |
| Docker images | Dockerfiles + compose (api, web, postgres, redis) | Daemon down → compose **NOT VERIFIED** today. |
| Real LLM | Provider code + MockTransport | No live key this session → live LLM **BLOCKED** until a secret is supplied without printing it. |
| Observability production | `/metrics` + OTel SDK in tests | No live collector, no CloudWatch export verified. |
| Load testing API | SQLite Locust: 25 users → **89.97% fail** (write lock) | Postgres+Redis 100% success claim in STATUS.md is **not reproduced**. |

### CODE-READY (implemented, not live-verified)

- Distilled router model artifacts (runtime; gateway still uses **heuristic** `router_decide`)
- Kafka-style producer/consumer/DLQ **interface** (`InMemoryBroker` only; `kafka-python` **not** in `app/requirements.txt`)
- PySpark `app/spark/pipeline.py` (mock-tested only if pyspark installed; currently skipped)
- Airflow DAG `ml/airflow_dags/prometheus_dag.py`
- Bedrock provider (fail-closed without creds)
- pgvector vector store path
- Gated deploy workflow (manual `workflow_dispatch` + `production` environment)

### NOT VERIFIED

- Live Kafka broker, consumer groups, lag, broker restart
- Live Postgres EXPLAIN ANALYZE / concurrent writes / reconnect
- Live Redis Lua limiter / cache / fallback
- Gateway → ML inference routing (timeout, circuit breaker, fallback metrics)
- Kind/k3d/EKS/Fargate apply, HPA behavior, rolling update, rollback
- Terraform validate/plan/apply
- Docker compose up
- PySpark job execution
- Airflow scheduler/DAG run
- OIDC/SSO
- Container/image scan on this host
- AWS Budgets / actual cloud spend

### BLOCKED

| Item | Why |
|---|---|
| Autonomous AWS apply | Caller is **ROOT**. Safety rule: do not use root for routine infra. Need IAM deploy user/role + MFA/SSO. |
| AWS apply this phase | Phase 0 forbids resource creation. Phase 5 requires explicit approval + cost gate. |
| GPU / large EC2 | Budget ~$197; not justified. |
| Live LLM E2E | No validated provider key in this session. |
| Local compose / K8s cluster | Docker Desktop stopped; no Kubernetes API. |
| Spark execution | No JVM. |
| Terraform CLI | Not installed. |

## 4. Stale documentation (fix in later phases)

- `PROJECT_HANDOFF.md`: HEAD `7eccddc`, 79 tests, Redis/Postgres “NOT VERIFIED”, ML live “NOT VERIFIED” — all superseded.
- `STATUS.md` / `RESUME_EVIDENCE.md`: pre-`fba6cb0`; AWS STS rejection outdated; Postgres load 100% unproven.
- `LOAD_TESTING.md` / API section of `BENCHMARKS.md`: SQLite-only; does not mention Redis Lua or PG pool.
- `docs/AWS_DEPLOYMENT.md`: still says STS rejects keys — **false** as of 2026-09-04 (STS works; identity is root).
- Terraform `var.aws_region` default `us-east-1` vs operator region `ap-south-1`.
- Handoff “Kafka-python-ng compatible client” vs no kafka client dependency.
- Alembic downgrade of `048fa8e0c0dc` recreates a `document_vectors` table that is not part of the upgrade — **do not run that downgrade**.

## 5. Security risks (current)

1. **Root AWS identity** for any apply → full account blast radius, no IAM boundary, CloudTrail attribution is “root”.
2. K8s Secret YAML contains placeholder stringData (must never become real keys in git).
3. Compose Postgres password is a **local demo** value in `docker-compose.yml` (not an AWS secret). Fine for laptop; never reuse in AWS.
4. `skip_final_snapshot=true` and `force_destroy` on S3 in Terraform = demo teardown posture, not enterprise backup policy.
5. Lambda image `:latest` in Terraform (mutable tags).
6. No SSO; API keys only.
7. pip-audit in CI uses `|| true` (does not fail the job).

## 6. Cost risks (if `enable_aws=true` in `ap-south-1`)

Indicative **design** numbers from `docs/cost_model.md` (us-east-1 list, not re-priced this phase):

| Resource | Purpose | Idle / floor risk |
|---|---|---|
| Aurora Serverless v2 0.5–2 ACU | Production Postgres + pgvector | **Cannot scale to 0**; ~$43/mo class floor; stop cluster between demos |
| Interface VPC endpoints | Secrets/Bedrock without NAT | ~$7/mo each if enabled |
| NAT Gateway | Explicitly **off** (`create_nat_gateway=false`) | Would consume ~17% of $197 |
| Lambda + APIGW + ECR | API compute | Idle ~$0 if no traffic (image still in ECR) |
| S3 + Secrets Manager + CloudWatch | Corpus, DB password, logs | Low unless log volume |
| Bedrock on-demand | Real LLM | Token spend unbounded without app kill-switch + account budgets |
| GPU / always-on Fargate / multi-AZ replicas | — | **Out of budget; do not create** |

Full enabled stack continuously ~$70–80/mo in the cost model (region may differ). **$197 credits ≈ 2–2.5 months** if Aurora is left running. GPU would blow the budget immediately.

**Do not apply Terraform until:** least-privilege IAM principal, `aws_region=ap-south-1`, AWS Budget alarm, and explicit human APPLY.

## 7. Proposed AWS architecture (cost-first, evidence-preserving)

Keep the **existing Terraform shape** (Lambda scale-to-zero, no NAT, Aurora SV2 cap 2 ACU, ECR lifecycle 3 images). Do **not** rewrite to Fargate/EKS unless Phase 4 local k8s is insufficient evidence.

**Recommended evidence split:**

1. **Laptop / Docker (Phases 1–4, 6):** Postgres, Redis, Kafka (KRaft or Redpanda), API, ML inference, optional kind cluster. Highest engineering evidence per dollar ($0 AWS).
2. **AWS foundation only after approval (Phase 5A):** IAM deploy role (not root), account Budget + SNS, ECR, private S3, Secrets Manager, CloudWatch log groups, resource tags. No Aurora yet.
3. **AWS data plane (5B) only if credits remain after 5A:** Aurora SV2 0.5 ACU **with a calendar stop**, ElastiCache **or** skip managed Redis and keep Redis in the same task for cost.
4. **AWS app (5C):** Lambda+APIGW **or** single small Fargate only if Lambda image/SSE proves too constrained. Default: existing Lambda path.
5. **ML on AWS (5D):** CPU-only same image as `ml_service`; no GPU.
6. **Bedrock (5E):** only with Secrets Manager + daily token budget; otherwise keep mock and mark BLOCKED.

## 8. Proposed AWS resources (inventory of current Terraform if enabled)

VPC + 2 private subnets; API + DB security groups; S3 gateway endpoint; optional interface endpoints; IAM roles (API Lambda, FinOps); ECR repo + lifecycle; Lambda API + FinOps; HTTP API Gateway; Aurora cluster + 1 serverless instance + subnet group + parameter group (vector); Secrets Manager DB secret; S3 corpus bucket (private, encrypted, versioned, lifecycle); EventBridge scheduler + budget-alert rule; CloudWatch log groups, dashboard, alarms.

Every resource is `count = var.enable_aws`. Default plan should be **zero creates**.

## 9. Deployment dependencies (local → cloud)

1. Docker Desktop (or another engine) for Postgres/Redis/Kafka/kind  
2. Least-privilege IAM (not root) + `ap-south-1` Terraform var  
3. Terraform CLI  
4. Container registry login (ECR)  
5. Optional: valid LLM secret in Secrets Manager  
6. Human APPLY for any `enable_aws=true`

## 10. Recommended deployment order

| Order | Phase | Goal | AWS? |
|---|---|---|---|
| 0 | This document | Honest baseline | No |
| 1 | Postgres + Redis live | Migrations, pool, Lua limiter, EXPLAIN, concurrency | No |
| 2 | Local Kafka/Redpanda | Producer, CG, retry, DLQ, restart | No |
| 3 | ML router in gateway | HTTP client + timeout + CB + heuristic fallback + metrics | No |
| 4 | kind/k3d | Apply manifests, probes, scale, rollback | No |
| 5 | AWS **gate** | Plan + cost + IAM; **STOP for approval** | Plan only |
| 5A–F | Foundation → DB → app → ML → LLM → o11y | Only after approval | Yes, staged |
| 6 | Airflow + Spark | Execute, don’t parse | Prefer local/containers |
| 7–8 | Security + CI | Scans, gated deploy, no auto-prod | Secrets in GH, not root keys |
| 9–10 | Benchmarks + final audit | Measured only | Mix |

## 11. Phase 0 verdict

**PASS (audit complete).** No fundamental code defect blocks Phases 1–4.

**Does not block continuing locally:** root AWS identity (blocks only Phase 5 apply), Docker down (Phase 1 dependency), missing terraform/java/k8s.

**Do not start Phase 5 resource creation** until a non-root principal exists and the user approves the costed plan.

### Remaining work after Phase 0

- Start Docker (or equivalent) and execute Phase 1 against real Postgres/Redis  
- Wire/verify Kafka broker locally (Phase 2)  
- Integrate learned router into `run_chat_pipeline` with fallback (Phase 3)  
- Bring up a local cluster for Phase 4  
- Install Terraform; align region; create IAM deploy role; **stop before apply**  
- Refresh STATUS / HANDOFF / RESUME_EVIDENCE after measured phases  
- Fix Alembic downgrade footgun; fail CI on pip-audit; pin TF region to `ap-south-1` when planning
