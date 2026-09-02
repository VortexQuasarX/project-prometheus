# Security

## Implemented (VERIFIED)

- **API-key auth**: SHA-256 at rest, `hmac.compare_digest`, inactive-key 403
- **RBAC**: 6 roles × 19 permissions enforced server-side (app/core/rbac.py),
  every protected endpoint mapped and matrix-tested (tests/test_rbac.py)
- **Multi-tenancy**: organization-scoped queries + isolation tests
- **Input validation**: Pydantic v2 on every mutating endpoint
- **Rate limiting**: sliding window per key; keyless traffic rate-limited by IP
- **PII masking / prompt-injection / unsafe-content guardrails** with zero-cost
  refusals and audit events
- **Audit**: append-only `audit_events`, admin-only read
- **Secrets**: `.env` only; `ADMIN_API_KEY=***` placeholder pattern; secret scan
  in the delivery pipeline; CI bandit (B101/B104 skipped with rationale)

## V2 (FUTURE)

- SSO/OIDC (integration seam documented; no insecure fake auth shipped)
- Postgres row-level security for hard tenant isolation
- TLS termination (Ingress + cert-manager manifests shipped in infra/k8s)
- Container scanning in CI (pip-audit added; Trivy next)
- Rotation for API keys (admin UI)
