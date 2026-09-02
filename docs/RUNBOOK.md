# RUNBOOK

## Start / stop

```powershell
# start (two terminals)
uvicorn app.main:app --port 8000          # backend
cd web ; npm run dev                       # frontend
# stop: Ctrl+C on each
```

## Common operations

| Symptom | Action |
|---|---|
| 429 on chat | expected: rate limit per key. Raise `RATE_LIMIT_PER_MINUTE` in policy or env |
| 500 + "database is locked" | SQLite write contention: reduce concurrency (single worker) or migrate to Postgres (docs/LOAD_TESTING.md) |
| Kill switch active | `POST /api/v1/budget/kill-switch {"kill_switch_mode":"off"}` (admin) |
| Pending approval stuck | `GET /api/v1/agents/actions` → approve/reject with an admin key |
| Drift alert fired | `python -m app.ml.retrain` (promotion gate protects production) |
| Demo data stale | `python scripts/reset_demo.py` (recreates keys — update Settings) |
| Model artifact missing | `python -m app.ml.train` then restart ml_service |

## Health endpoints

- API: `GET /api/v1/health` (status+db)
- ML inference: `GET /health`, `GET /ready` (503 when model missing)

## Escalation

Everything is observable: `/metrics` (Prometheus), traces
(`/api/v1/traces/{id}`), audit (`/api/v1/audit`), dead-letter
(`failed_requests` table).
