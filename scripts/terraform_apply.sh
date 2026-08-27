#!/usr/bin/env bash
# terraform_apply.sh — REFUSES to run without an explicit APPLY.
#
# Usage:  ./scripts/terraform_apply.sh APPLY
#   or:   CONFIRM_APPLY=yes ./scripts/terraform_apply.sh APPLY
#
# The script plans first, asks for a second confirmation, and never uses
# -auto-approve. COST WARNING: Aurora Serverless v2 has a 0.5 ACU floor
# (~$43/mo) — stop the cluster between demo windows and destroy afterwards.
set -euo pipefail

if [ "${1:-}" != "APPLY" ] && [ "${CONFIRM_APPLY:-}" != "yes" ]; then
  echo "Refusing to apply."
  echo "Pass APPLY as the first argument (or set CONFIRM_APPLY=yes) after reviewing the plan."
  exit 1
fi

command -v terraform >/dev/null 2>&1 || {
  echo "terraform not found. Install it first."
  exit 1
}

cd "$(dirname "$0")/../infra"

echo "COST WARNING: this stack can cost ~\$70-80/mo if left running."
echo " - Aurora Serverless v2 floor 0.5 ACU (~\$43/mo): STOP the cluster between demos."
echo " - No NAT gateway by default. VPC endpoints only."
echo " - Destroy the stack after the demo window."
echo

terraform init -input=false
terraform validate
terraform plan -var enable_aws=true -out=tfplan

read -r -p "Type 'yes' to apply the reviewed plan: " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted. Nothing was applied."
  exit 1
fi

terraform apply -input=false tfplan

echo
echo "Reminder: after the demo, stop the Aurora cluster (aws rds stop-db-cluster)"
echo "or run 'terraform destroy' to protect the \$197 budget."
