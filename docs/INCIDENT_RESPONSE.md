# INCIDENT_RESPONSE

## Severity ladder

- SEV1: API down / block_all kill switch stuck / data exposure
- SEV2: elevated 500s (DB contention), provider outage, drift alarm
- SEV3: single-user anomalies, stale approvals

## Playbooks

### 1. Cost spike / budget breach (SEV2)
1. `GET /api/v1/budget` → confirm state (warning/critical/exceeded)
2. If exceeded: the system auto-escalates to `cheap_only` (audit event)
3. Manual containment: `POST /api/v1/budget/kill-switch {"kill_switch_mode":"block_all"}`
4. Investigate: `GET /api/v1/cost-report`, `/api/v1/traces`
5. Recovery: fix cause → set kill switch back to `off` (audited)

### 2. Unsafe outputs / guardrail bypass (SEV1)
1. `kill_switch_mode=block_all` immediately
2. `GET /api/v1/audit` filter `guardrail.blocked` for samples
3. Tighten policy (prompt_injection_detection_enabled, restricted topics)
4. Never edit audit rows (append-only by design)

### 3. Provider outage (SEV2)
1. Pipeline already dead-letters failures (`failed_requests`) and returns 503
2. Flip `LLM_PROVIDER=mock` (keeps the platform serving cached/governed answers)
3. Restore provider, then clear the kill switch if engaged

### 4. DB lock storms (SEV2, SQLite-specific)
1. Evidence: 500s + "database is locked" (see docs/LOAD_TESTING.md)
2. Mitigate: reduce concurrency / restart worker
3. Fix: migrate to Postgres (`DATABASE_URL`, alembic upgrade head)

## Post-incident

Write a timeline from `/api/v1/audit` (append-only) + traces; record model
transitions in `ml/artifacts/model_history.json`; never delete audit rows.
