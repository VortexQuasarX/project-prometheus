# -----------------------------------------------------------------------------
# Outputs — null-safe with respect to the enable_aws count-gating (no errors
# when the stack is disabled).
# -----------------------------------------------------------------------------
output "api_url" {
  description = "Public API base URL."
  value       = var.enable_aws ? (var.compute_platform == "lambda" ? aws_apigatewayv2_api.api[0].api_endpoint : null) : null
}

output "db_endpoint" {
  description = "PostgreSQL database endpoint."
  value       = var.enable_aws ? aws_db_instance.postgres[0].endpoint : null
}

output "ecr_repository_url" {
  description = "ECR repository URL for the API image."
  value       = var.enable_aws ? aws_ecr_repository.api[0].repository_url : null
}

output "s3_bucket_name" {
  description = "RAG corpus bucket."
  value       = var.enable_aws ? aws_s3_bucket.corpus[0].bucket : null
}

output "secrets_arns" {
  description = "Secrets Manager ARNs created by the stack."
  value       = var.enable_aws ? [aws_secretsmanager_secret.db_credentials[0].arn] : []
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL."
  value = var.enable_aws ? "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.overview[0].dashboard_name}" : null
}

output "lambda_function_url" {
  description = "Direct Lambda Function URL."
  value       = var.enable_aws && var.compute_platform == "lambda" ? aws_lambda_function_url.api[0].function_url : null
}
