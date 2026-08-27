# Cost Model

Two layers of cost control — do not conflate them:

1. **Operational token spend** — what LLM calls cost while the system runs.
2. **Cloud credit burn** — what the AWS stack itself costs against the **$197 credit**.

## Token Pricing (mock catalog, configurable in `app/cost/pricing.py`)

| Model | input /1k | output /1k | cache read /1k | cache write /1k |
|---|---|---|---|---|
| mock-small | $0.0050 | $0.0150 | $0.0010 | $0.0020 |
| mock-large | $0.0200 | $0.0600 | $0.0040 | $0.0080 |
| bedrock-cheap | $0.0030 | $0.0150 | $0.0010 | $0.0020 |
| bedrock-strong | $0.0300 | $0.1500 | $0.0030 | $0.0060 |

- **Request cost** = `(input_tokens × in + output_tokens × out)/1000` (+ cache-write leg on the miss that populates the cache).
- **Cache savings** = would-have LLM cost − cache-read cost, recorded per hit in `usage_records.cache_saved_usd`.
- Sanity: a typical mock-small request (1k in + 500 out) ≈ **$0.0125**; the $2.00 daily budget ≈ 160 such requests; 20 expensive mock-large calls ≈ $1.00/day. Budgets are demonstrable, not decorative.

## Policy Levers (token spend)

`daily_budget_usd` (warning ≥70%, critical ≥90%, exceeded ≥100% → auto `cheap_only`), `request_budget_usd` (pre-flight downgrade/403), `max_input/output_tokens`, `expensive_models` + `expensive_model_limit_per_day`, `rate_limit_per_minute`, kill switch modes `off/cache_only/cheap_only/block_all`.

## Mock Mode ($0)

`LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`, `VECTOR_STORE_PROVIDER=local`, `CACHE_PROVIDER=local`, SQLite — no AWS SDK calls, no network, no API keys. BedrockProvider lazy-imports boto3 and fails closed with a controlled error; local mode never reaches it.

## Serverless / Scale-to-Zero (AWS path)

- **Lambda (arm64, 512MB)** for the API — idle $0 (vs Fargate ~$9-11/mo floor). SSE via response streaming.
- **No NAT gateway** (≈$33/mo = 17% of the credit) — S3 gateway endpoint (free) + secretsmanager/bedrock-runtime interface endpoints only when enabled.
- **Aurora Serverless v2**: 0.5-2.0 ACU. Floor ≈ $43/mo and it cannot pause — **stop the cluster between demo windows**; storage (~$0.10/GB/mo) continues. `skip_final_snapshot=true` is demo-only.
- **Logs/metrics**: 7-day retention, ≤10 custom metrics, ≤3 dashboards (free tier covers them). No Bedrock invocation logging by default.
- **ECR** lifecycle keeps 3 images; **S3** lifecycle: STANDARD_IA at 30d, expire at 90d.
- Indicative enabled-state run rate: ~$70-80/mo continuously — **the operating model is apply → demo → stop Aurora / destroy**, landing a 2-week demo window around $35-45, inside $197 with margin.

## Kill Switch (and what it does NOT do)

The in-app kill switch caps **token spend**. It cannot stop AWS infrastructure charges — that is the job of `enable_aws=false`, the APPLY-gated scripts, and destroy/stop discipline. Both layers are documented here and in `docs/COST_MODEL.md` on purpose.
