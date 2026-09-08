# -----------------------------------------------------------------------------
# Compute — API Gateway HTTP API + Lambda (scale-to-zero) + ECR.
#
# DECISION (see docs/ARCHITECTURE.md): Lambda over Fargate because the spec
# demands "prefer serverless and scale-to-zero" — Lambda idle costs $0 while
# Fargate bills ~$9-11/mo even idle. SSE is served via Lambda response
# streaming (function URL behind API Gateway). A commented Fargate alternative
# sits at the bottom for teams needing long-lived WebSockets.
#
# The spec tree has no apigateway.tf / ecr.tf; both fold into this file.
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "api" {
  count = var.enable_aws ? 1 : 0

  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = 7 # logs are $0.50/GB — keep retention short

  tags = { Name = "${var.project}-api-logs" }
}

resource "aws_cloudwatch_log_group" "finops" {
  count = var.enable_aws ? 1 : 0

  name              = "/aws/lambda/${var.project}-finops"
  retention_in_days = 7

  tags = { Name = "${var.project}-finops-logs" }
}

resource "aws_ecr_repository" "api" {
  count = var.enable_aws ? 1 : 0

  name                 = "${var.project}/api-${random_string.suffix.result}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "${var.project}-api-ecr" }
}

# Keep only the last 3 images — ECR storage is $0.10/GB/mo and CI pushes add up.
resource "aws_ecr_lifecycle_policy" "api" {
  count = var.enable_aws ? 1 : 0

  repository = aws_ecr_repository.api[0].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_lambda_function" "api" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  function_name = "${var.project}-api"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api[0].repository_url}:latest"
  architectures = ["x86_64"]

  memory_size = 512
  timeout     = 900 # SSE streams are long-lived

  vpc_config {
    subnet_ids         = [for subnet in aws_subnet.private : subnet.id]
    security_group_ids = [aws_security_group.api[0].id]
  }

  environment {
    variables = {
      APP_ENV                 = "production"
      LLM_PROVIDER            = "bedrock"
      EMBEDDING_PROVIDER      = "bedrock"
      VECTOR_STORE_PROVIDER   = "pgvector"
      CACHE_PROVIDER          = "local"
      DATABASE_URL            = "postgresql://prometheus_admin:${random_password.db_master[0].result}@${aws_db_instance.postgres[0].endpoint}/${var.db_name}"
      ADMIN_API_KEY           = "prometheus-admin"
      BEDROCK_REGION          = var.aws_region
      BEDROCK_CHEAP_MODEL_ID  = "apac.amazon.nova-micro-v1:0"
      BEDROCK_STRONG_MODEL_ID = "apac.amazon.nova-lite-v1:0"
      BEDROCK_MODEL_ID        = "apac.amazon.nova-micro-v1:0"
      CORS_ORIGINS            = "[\"*\"]"
    }
  }

  role = aws_iam_role.api[0].arn

  tags = { Name = "${var.project}-api" }
}

resource "aws_lambda_function_url" "api" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  function_name      = aws_lambda_function.api[0].function_name
  authorization_type = "NONE"

  depends_on = [aws_cloudwatch_log_group.api]
}

# API Gateway HTTP API in front of the function URL.
resource "aws_apigatewayv2_api" "api" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  name          = "${var.project}-api"
  protocol_type = "HTTP"
  target        = aws_lambda_function.api[0].arn

  tags = { Name = "${var.project}-api" }
}

resource "aws_lambda_permission" "api_gateway" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal     = "apigateway.amazonaws.com"
}

resource "aws_lambda_permission" "url" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  statement_id           = "AllowFunctionURLInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api[0].function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# FinOps scheduled Lambda (target of the EventBridge scheduler).
resource "aws_lambda_function" "finops" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  function_name = "${var.project}-finops"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api[0].repository_url}:latest"
  architectures = ["x86_64"]

  memory_size = 256
  timeout     = 300

  environment {
    variables = {
      FINOPS_ENTRYPOINT = "scheduled_finops_review"
    }
  }

  role = aws_iam_role.api[0].arn

  tags = { Name = "${var.project}-finops" }
}

resource "aws_lambda_permission" "scheduler" {
  count = var.enable_aws && var.compute_platform == "lambda" ? 1 : 0

  statement_id  = "AllowSchedulerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finops[0].function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.finops_daily[0].arn
}

# # Fargate alternative (kept for V2 when WebSockets need a long-lived process):
# resource "aws_ecs_cluster" "api"    { count = var.compute_platform == "fargate" ? 1 : 0; name = "${var.project}-cluster" }
# resource "aws_ecs_task_definition"  { ... }
# resource "aws_ecs_service"          { ... }
