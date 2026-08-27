# Agentic Design

## Runtime

Every agent run is a persisted state machine, not a prompt wrapper:

| Field | Meaning |
|---|---|
| `run_id` | Unique id (`run_xxxxxxxx`) |
| `agent_type` | `finops` / `reliability` / `evaluator` / `guardrail` / `router` |
| `trigger` | `manual` / `budget_threshold` / `cache_hit_rate_low` / `expensive_model_overuse` / `repeated_similar_queries` / `latency_increasing` |
| `status` | `pending → running → waiting_approval → approved → applied → verified`, plus `rejected`, `failed` |
| `plan` | Step descriptors built by the planner |
| `steps` | Executed step records (name/status/input/output/duration) |
| `tool_calls` | Exact `{tool, input, output, duration_ms, status}` log rows |
| `observations` | Metric snapshots gathered via tools |
| `recommendation` | `{title, expected_monthly_saving_usd, risk_level, latency_impact}` |
| `approval_status` | `none / pending / approved / rejected` |

## Tools

FinOps tool registry (each call is measured and logged):

`get_usage_metrics`, `get_cache_stats`, `get_model_costs`, `get_latency_report`, `simulate_routing_policy`, `simulate_cache_threshold`, `estimate_savings`, `create_action_plan`, `request_human_approval`, `apply_local_policy`, `write_audit_event`

Reliability tools: `recommend_fallback_model`, `recommend_cache_only`, `recommend_retry_policy`, `create_alert`.

## State Machine

```
pending ──► running ──► waiting_approval ──(approve)──► approved ──► applied ──► verified
                │                │
                │                └──(reject)──► rejected
                └──(uncaught error)──► failed
```

SSE events fire at each transition: `agent_started`, `action_pending_approval`, `action_approved`, `action_applied`, `agent_completed`.

## FinOps 11-Step Flow

1. **Gather metrics** — `get_usage_metrics`, `get_cache_stats`, `get_model_costs`, `get_latency_report`.
2. **Detect inefficiency** — budget threshold crossed, cache hit rate < 0.5, expensive-model overuse ≥ limit, repeated similar queries, p95 vs avg latency spread, manual trigger.
3. **Generate hypotheses** — planner turns observations into evidence-backed hypotheses.
4. **Simulate policy changes** — `simulate_routing_policy` (shift expensive traffic to cheap at ~25% cost), `simulate_cache_threshold` (hit-rate gain per threshold slack).
5. **Estimate savings** — `estimate_savings` combines legs into `expected_monthly_saving_usd`.
6. **Assess risk** — low/medium/high by blast radius (routing shift = low; kill switch = high).
7. **Create action plan** — pending `agent_actions` rows (first manual action gets the canonical `action_101`).
8. **Request human approval** — run parks at `waiting_approval` (SSE `action_pending_approval`); skipped only when `require_human_approval=false`.
9. **Apply approved policy** — `apply_local_policy` through the policy engine (version bump + audit); run → `applied`.
10. **Verify outcome** — subsequent metrics confirm the change; run → `verified`.
11. **Write audit event** — every transition lands in the append-only `audit_events`.

## Why This Is More Than A Prompt

- Numbers come from **tools over real telemetry** (usage records, cache counters, request latencies), not LLM guesses.
- Savings are **simulated before applied** and the delta is policy-versioned and auditable.
- Nothing mutates governance state without a **human decision** recorded with actor + note.
