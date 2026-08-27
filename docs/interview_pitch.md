# Interview Pitch

## 30-Second Pitch

"I built Prometheus, an agentic AI governance and FinOps control plane. Every LLM request goes through one pipeline: guardrails, a routing agent, a semantic cache, RAG grounding, an evaluator, and per-request cost accounting. A FinOps agent watches the telemetry, simulates a policy change — like routing FAQs to a cheaper model — files the expected savings, and asks a human for approval before applying it, fully audited. It runs entirely in mock mode at zero cost, and the Terraform path to Bedrock is cost-gated behind an explicit APPLY."

## 2-Minute Interview Answer

"Teams adopting LLMs get blind-sided by token costs, unsafe prompts, and zero auditability. Prometheus treats cost, quality, and policy as pipeline stages, not dashboards bolted on afterwards.

The chat pipeline has twelve steps — every one emits a trace event, so any answer can be replayed with its full decision trail: which guardrail ran, what the router chose and why, whether the cache hit and how much that saved, what the evaluator scored. The semantic cache uses deterministic hash embeddings with version-aware invalidation — policy changes instantly invalidate stale answers, and hits record real savings.

The interesting part is the FinOps agent. It's not a prompt wrapper — it's a state machine with a tool registry. It gathers usage metrics, cache stats, and model costs as tool calls that are logged with durations; it simulates a routing policy change and estimates savings from real telemetry; then it files an action and stops at `waiting_approval`. A human approves, the policy engine applies the change with a version bump, the change is audited, and the run verifies the outcome afterwards.

Governance is enforced, not decorative: policies are versioned JSON with audited changes; guardrails mask PII or block hard with zero cost; a kill switch has four escalation modes; and the whole cloud path is count-gated Terraform where the default plan creates zero resources — because the $197 budget matters as much as the tokens.

It's testable — 48 tests cover the pipeline, cache, cost math, kill switch, guardrails, approvals, evals and traces — and it runs in mock mode with no AWS account at all."

## Hard Questions (and honest answers)

**Why Lambda over Fargate?** The spec demands scale-to-zero; Lambda idle is $0 and Fargate is ~$9-11/mo floor. The API is I/O-bound (LLM calls, DB). SSE works via Lambda response streaming; the Fargate alternative stays in Terraform as a documented variant for long-lived WebSockets.

**How is the $197 protected?** Two layers. Tokens: mock defaults, cache, budgets, kill switch. Infra: `enable_aws=false` default (plan shows 0 resources), no NAT gateway, Aurora stop/destroy discipline, ECR lifecycle, 7-day logs. The cost-safety contract lives in the first lines of `infra/main.tf`.

**Aurora can't scale to zero — why still Serverless v2?** It's the managed pgvector path with a 0.5-ACU floor. Mitigation is operational: stop the cluster between demo windows, destroy after. The cost is documented, not hidden.

**How do you prevent the cache from serving stale answers after a policy change?** The cache key includes `policy_version`, `kb_version`, and `cache_version`; any policy PUT or document ingest bumps a version and entries become invisible immediately. It's in tests.

**Isn't regex-based PII detection weak?** It's the right MVP scope: deterministic, testable, and fast. The GuardrailResult interface (block vs mask, reasons, risk) is the seam — swap in Presidio or a model behind the same contract in V2.

**What breaks first at scale?** SQLite's single writer. The schema and outbox design are portable to Postgres/Aurora (pgvector path already written); WAL + short transactions + a threadpool keep the MVP honest up to demo scale.

**Why synchronous chat instead of streaming tokens?** Deterministic cost/trace/audit per request is the product. Streaming tokens is a UI concern layered on later; the pipeline's contract is already per-request.

**What would you cut if you had one week?** Nothing in the governance loop — that's the thesis. I'd cut advanced charts first: they demo well but carry no enforcement semantics.
