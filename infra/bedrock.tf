# -----------------------------------------------------------------------------
# Bedrock — on-demand model invocation ONLY.
#
# COST TRAP: never create provisioned model throughput (hourly billing that
# dwarfs everything else in this stack). IAM scoping lives in iam.tf; model
# ids come from the environment (BEDROCK_MODEL_ID, empty in mock mode).
# Invocation logging is deliberately OFF by default (double CloudWatch billing).
# -----------------------------------------------------------------------------
data "aws_bedrock_foundation_models" "available" {
  count = var.enable_aws ? 1 : 0
}

# Example of what NOT to create:
# resource "aws_bedrock_provisioned_model_throughput" "never" { ... }
