# Architecture

## System Design

Prometheus is a single control plane with two sides:

- **Data plane (per request)**: `/api/v1/chat` executes a synchronous 12-step pipeline. Every step emits a canonical trace event. The pipeline is deliberately synchronous — it makes costs, traces and audits deterministic and testable.
- **Control plane (per action)**: agents (FinOps/Reliability) run through an orchestrator with a tool registry and a human-approval gate. Policy changes flow only through the versioned policy engine, which audits and bumps `policy_version` (which invalidates the semantic cache).

### Local MVP vs AWS Production

| Concern | Local MVP | AWS production path (enable_aws=true) |
|---|---|---|
| API | uvicorn (single worker) | API Gateway HTTP API + Lambda arm64 (response streaming for SSE) |
| LLM | MockLLMProvider (deterministic) | BedrockProvider (lazy boto3, retries+backoff, model-ARN-scoped IAM) |
| Embeddings | hashlib feature hashing, 256-dim | Amazon Titan embeddings |
| Vector store | LocalVectorStore (in-memory + JSONL) | PgVectorStore (Aurora Serverless v2, `CREATE EXTENSION vector`) |
| DB | SQLite (WAL, busy_timeout 5s) | Aurora PostgreSQL 15.x |
| Secrets | .env | Secrets Manager |
| Scheduler | manual trigger / cron | EventBridge Scheduler (daily 09:00 UTC) → FinOps Lambda |

### Data Flow (chat)

1. `request_received` (+SSE `request_started`) — request_id assigned (or replayed for idempotency).
2. `auth_checked` — X-API-Key → `api_keys` row (SHA-256 at rest, hmac.compare_digest).
3. `rate_limit_checked` — sliding window per key (middleware).
4. `budget_checked` — policy + budget state; kill-switch gating on the **effective** model; request-budget pre-flight downgrade/403.
5. `guardrail_checked` — PII (mask-and-continue when masking enabled) or block (zero-cost refusal + audit).
6. `router_decided` — deterministic classify → decision + model.
7. `cache_checked` — cosine ≥ 0.82 against unexpired, version-matched entries.
8. hit → `cost_saved_usd` accounting + usage row (cost 0) → `cost_logged` → `response_returned`.
9. miss → `retrieval_completed` (top-k chunks) → grounded prompt → `llm_called` → `evaluation_completed` (optional one strong-model retry) → cache put (if cacheable) → `cost_logged` → budget re-check → audit → `response_returned`.

### Agent Flow

`POST /agents/run` → orchestrator creates `agent_runs` row → plan built (planner) → runner executes steps → every tool call lands in `agent_tool_calls` with duration/status → findings recorded as steps → if `require_human_approval`, run parks at `waiting_approval` and an `agent_actions` row (e.g. `action_101`) goes pending → `POST /agents/actions/{id}/approve` applies the policy delta through the policy engine (bump + audit) → run becomes `applied` → a follow-up verification marks it `verified`.

## Engineering Notes (the parts that usually break)

- **SQLAlchemy reserved names**: JSON metadata columns are declared as attribute `details` mapped to column `metadata` — the declarative API reserves `metadata`.
- **`autoflush=False` sessions**: `SemanticCache._ensure_meta` flushes explicitly so subsequent queries see the reserved meta rows.
- **SQL LIKE wildcards**: reserved-key filtering uses `NOT IN` on `__stats__`/`__version__` — `startswith("__")` compiles to `LIKE '__%'` where `_` is a wildcard and matches everything.
- **Deterministic mock embeddings**: hashlib-based feature hashing (never builtin `hash()`, which is per-process salted) so cache tests and cache hits survive restarts.
- **SSE without a broker**: transactional-outbox (`sse_events`) written in-transaction with domain writes; the stream replays the last 10 minutes then polls every 400ms with 15s keepalives. Browsers' `EventSource` cannot send `X-API-Key`, so the UI proxies `/api/v1` through a Next.js rewrite (same-origin).
- **Eval harness**: calls the chat *service layer* in-process (same pipeline, full traces) — deterministic, no HTTP recursion.
