# Roadmap

## V1 — Local MVP (this repository, complete)

- FastAPI control plane: 12-step chat pipeline, 25+ endpoints under `/api/v1`
- Semantic cache (deterministic hash embeddings, version-aware invalidation, cost-saved accounting)
- Deterministic router + guardrails + rule-based evaluator
- Agent runtime with FinOps 11-step flow, tool registry, human-approval gate
- Policy engine (versioned, audited), budget states, kill switch modes
- Observability: 12 canonical trace events, SSE transactional outbox, dead-letter table
- Evaluation harness (10+ golden cases, 8 metrics)
- Next.js 12-page dashboard (TanStack Query, Recharts, dark mode, SSE invalidation)
- Terraform stack (count-gated, `enable_aws=false`), CI (ruff/pytest/frontend/docker), gated deploy
- Seed/reset scripts, Docker compose, Makefile, docs, tests

## V2 — AWS Production Path

- Flip `enable_aws=true`: API Gateway + Lambda arm64 (response-streaming SSE), Aurora Serverless v2 + pgvector, Secrets Manager, S3 corpus, ECR
- BedrockProvider live (Claude Haiku/Sonnet, Titan embeddings) behind model-ARN-scoped IAM
- Judge-LLM evaluator (rule-based judge stays as the fast path)
- OpenTelemetry export adapter → X-Ray/Jaeger (the in-code no-op adapter is the seam)
- CloudWatch custom metrics wired to the dashboard + alarms
- FinOps Lambda on EventBridge schedule (daily review) + reactive budget-alert trigger
- Redis-backed semantic cache option for multi-worker scale-out

## V3 — Platform

- Multi-tenant SaaS: orgs, teams, per-tenant policies and budgets (real billing)
- SSO (OIDC) + full RBAC on top of the existing api_keys/role primitives
- Advanced agents: cross-model A/B savings experiments, automated threshold tuning with rollback
- Real-time anomaly detection on token spend (streaming stats + Alertmanager integration)
- Policy-as-code (GitOps policy changes with PR review → same audit trail)
- Marketplace of guardrail packs (industry-specific PII/(topic) rule sets)
