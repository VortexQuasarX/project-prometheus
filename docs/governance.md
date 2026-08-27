# Governance

## Policies

One active policy row (JSON body + `policy_version`). Every change validates against a Pydantic schema, writes a `policy_changes` row (old body, new body, actor, reason), bumps the version, and appends an audit event. `policy_version` participates in the semantic cache key — **every policy change invalidates cached answers**.

Default policy (spec verbatim + the documented `expensive_models` extension):

```json
{
  "daily_budget_usd": 2.0,
  "request_budget_usd": 0.05,
  "max_input_tokens": 1000,
  "max_output_tokens": 500,
  "allowed_models": ["mock-small", "mock-large"],
  "expensive_models": ["mock-large", "bedrock-strong"],
  "expensive_model_limit_per_day": 20,
  "require_cache_check": true,
  "require_rag": true,
  "require_evaluation": true,
  "require_human_approval": true,
  "pii_masking_enabled": true,
  "prompt_injection_detection_enabled": true,
  "rate_limit_per_minute": 30,
  "kill_switch_mode": "off"
}
```

## Guardrails

Lightweight regex/heuristics (MVP scope, deterministic and testable):

- **PII**: email, phone, credit card (Luhn-validated), Aadhaar-like (12 digits, first 2-9), secret/token patterns (`sk-…`, `AKIA…`, `ghp_…`, `xox…-`, `AIza…`, Bearer tokens, PEM blocks, high-entropy base64).
- **Unsafe content**: severity-tiered stems (violence, self-harm, sexual abuse, weapons/explosives manufacturing, drugs, malware, doxxing, fraud).
- **Prompt injection**: instruction-override phrases, jailbreak/`DAN`/`developer mode`, system-prompt reveal attempts, guardrail-bypass phrasing.
- **Restricted topics**: keyword sets per policy.
- **Budget/policy violations**: estimated request cost vs `request_budget_usd`; disallowed model requests.

Behavior tiers: **blocked** (unsafe/injection/restricted) → HTTP 200 chat-schema refusal, `guardrail_status="blocked"`, cost $0.00, **no LLM call, no cache write**, audit `guardrail.blocked`. **Masked** (PII with `pii_masking_enabled=true`) → query is masked and the pipeline continues; trace records `pii_masked: true`.

## Audit

`audit_events` is **append-only** (no update/delete paths in code): `event_id, actor, role, action, resource, request_id, metadata, created_at`. Admin-only read endpoint with actor/action filters. Every mutating endpoint, policy change, guardrail block, agent transition, and demo reset writes here. Production upgrade path: ship to an append-only store (S3 Object Lock / EventBridge archive) — the interface is already append-shaped.

## Approvals (human-in-the-loop)

Agent actions that would mutate governance state are created `pending` with `approval_required` from policy. `POST /agents/actions/{id}/approve` applies the policy delta **through the policy engine** (version bump + audit + cache invalidation) and moves the run `applied → verified`; `POST /reject` parks the run as `rejected`. Both record the deciding actor and note. When `require_human_approval=false`, actions auto-apply (still audited) — that flag is itself part of the audited policy.

## Kill Switch

`off / cache_only / cheap_only / block_all`, stored in the policy body and set through the policy engine (audited, version-bumping):

- `cache_only` — cache reads allowed; misses get a zero-cost refusal (no LLM).
- `cheap_only` — router restricted to non-expensive models; strong/expensive requests refused (`blocked_kill_switch`).
- `block_all` — every chat request returns a clean 403 envelope.

Budget escalation auto-sets `cheap_only` when daily spend reaches `exceeded`; escalation order is `off → cheap_only → block_all`.
