# Load Testing

**Tool:** Locust 2.46.4 · **Command:** see §Reproduce · **Environment:** local Windows host, uvicorn single worker, SQLite (WAL), mock LLM.

## Run 1 — default rate limit (30 req/min/key) ACTIVE

25 users, 60s. Result: the rate limiter correctly enforced 30 req/min per key —
806 clean HTTP 429 responses on POST /chat. **This is the governance system
working under load**, not a bug.

## Run 2 — 25 concurrent users, rate limit raised (5000/min)

| Metric | Value (measured) |
|---|---|
| Total requests | 927 |
| Aggregated failure rate | **89.97%** (834 requests) |
| Failure cause | HTTP 500 from SQLite write-lock contention (558 chat, 174 metrics, 102 cache-stats) |
| Healthy requests | 93 × GET /health (0 fails) |

## Finding (VERIFIED — measured, reproduced twice)

**SQLite's single-writer lock is the production concurrency boundary.** With
WAL + busy_timeout raised 5000ms→30000ms, sequential and light concurrent
traffic is healthy, but at ~25 concurrent writers the lock queue overflows and
writes fail with 500s. This is a documented SQLite limitation, not a bug in
the pipeline logic.

**Production fix (ROADMAP V2):** PostgreSQL/Aurora (row-level MVCC, no
single-writer lock) — the SQLAlchemy layer is already portable; the
`DATABASE_URL` swap plus Alembic migrations is the migration path.

## Reproduce

```bash
# terminal 1 — API with raised limit
RATE_LIMIT_PER_MINUTE=5000 uvicorn app.main:app --port 8000
# terminal 2
locust -f benchmark/locustfile.py --headless -u 25 -r 5 -t 60s \
  --host http://localhost:8000 --only-summary --csv benchmark/results
```

Artifacts: `benchmark/results_stats.csv`, `results_failures.csv`,
`results_stats_history.csv`, `results_exceptions.csv`.
