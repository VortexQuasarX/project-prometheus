#!/usr/bin/env bash
# Read-only Terraform plan (NEVER applies). Default: enable_aws=false.
set -euo pipefail

command -v terraform >/dev/null 2>&1 || {
  echo "terraform not found. Install: https://developer.hashicorp.com/terraform/downloads"
  exit 1
}

cd "$(dirname "$0")/../infra"

if [ "${1:-}" = "--aws" ]; then
  echo ">> Planning with enable_aws=true (READ-ONLY — nothing is created)"
  terraform fmt -check
  terraform validate
  terraform plan -var enable_aws=true
else
  echo ">> Planning with enable_aws=false (cost-safe dry plan)"
  terraform fmt -check
  terraform validate
  terraform plan -var enable_aws=false
fi
