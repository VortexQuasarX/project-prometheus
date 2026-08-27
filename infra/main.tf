# =============================================================================
# Project Prometheus — Terraform root
#
# COST-SAFETY CONTRACT: nothing is created unless enable_aws=true AND an
# explicit, human-approved `terraform apply` is run (scripts/terraform_apply.sh
# refuses unless the first argument is literally APPLY). With the default
# `enable_aws = false`, `terraform plan` shows 0 to create / 0 to change.
# =============================================================================
terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Local state for the MVP; move to an S3 backend before team use.
  backend "local" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = "prometheus"
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.tags,
    )
  }
}

# Globally-unique suffix for S3 / ECR names.
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}
