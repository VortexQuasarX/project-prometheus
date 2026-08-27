# -----------------------------------------------------------------------------
# Variables — every resource in this stack is gated on enable_aws (default
# false). Nothing below has any effect until an approved apply flips it on.
# -----------------------------------------------------------------------------
variable "enable_aws" {
  description = "MASTER COST SWITCH. When false, terraform plan creates nothing."
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region (matches .env.example)."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used for resource naming."
  type        = string
  default     = "prometheus"
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "VPC CIDR block."
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs (2 AZs required by RDS subnet groups)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "create_nat_gateway" {
  description = "NAT gateway costs ~$33/mo (~17% of the $197 credit). Keep false; use VPC endpoints instead."
  type        = bool
  default     = false
}

variable "enable_vpc_endpoints" {
  description = "Interface endpoints (~$7/mo each): secretsmanager + bedrock-runtime. S3 gateway endpoint is free."
  type        = bool
  default     = true
}

variable "compute_platform" {
  description = "lambda (scale-to-zero, default) or fargate (documented alternative)."
  type        = string
  default     = "lambda"
}

variable "aurora_min_acus" {
  description = "Aurora Serverless v2 floor is 0.5 ACU (~$43/mo) — it cannot scale to zero; stop the cluster between demo windows."
  type        = number
  default     = 0.5
}

variable "aurora_max_acus" {
  description = "Cap ACUs to bound cost."
  type        = number
  default     = 2.0
}

variable "db_name" {
  description = "Aurora database name."
  type        = string
  default     = "prometheus"
}

variable "backup_retention_days" {
  description = "Aurora backup retention (days)."
  type        = number
  default     = 7
}
