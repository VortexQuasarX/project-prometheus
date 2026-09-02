# AWS_DEPLOYMENT

**STATUS: NOT VERIFIED** — the Terraform path is complete and cost-gated but
has never been applied (spec rule: explicit APPLY only; stored AWS keys are
rejected by STS and must be replaced).

## Deploy sequence (after valid AWS credentials exist)

```bash
aws sts get-caller-identity                      # confirm identity
cd infra
terraform validate && terraform plan -var enable_aws=true   # review cost line-by-line
../scripts/terraform_apply.sh APPLY              # second confirmation gate
```

Post-apply:
1. Push images: `docker build/push` to the created ECR repo
2. Set `LLM_PROVIDER=bedrock` + `BEDROCK_MODEL_ID` in Lambda env
3. Point the frontend at the API Gateway URL (`outputs.api_url`)
4. Run `alembic upgrade head` against Aurora (pgvector)
5. Watch the CloudWatch dashboard; Aurora floor ≈$43/mo — **stop the cluster
   between demo windows** (`aws rds stop-db-cluster`)

## Cost discipline (VERIFIED design, unverified spend)

- `enable_aws=false` default → plan shows 0 resources
- Lambda scale-to-zero (no Fargate idle), no NAT (VPC endpoints), ECR keep-3,
  7-day logs, on-demand Bedrock only
- Kill switch caps token spend; enable_aws caps infra spend — two layers
