# -----------------------------------------------------------------------------
# IAM — least privilege. The API runtime may invoke specific Bedrock models,
# read exactly two secrets, write its own log stream, and put custom metrics.
# The FinOps scheduler may only invoke the finops Lambda.
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "api_assume" {
  count = var.enable_aws ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  count = var.enable_aws ? 1 : 0

  name               = "${var.project}-api-role"
  assume_role_policy = data.aws_iam_policy_document.api_assume[0].json

  tags = { Name = "${var.project}-api-role" }
}

data "aws_iam_policy_document" "api_policy" {
  count = var.enable_aws ? 1 : 0

  statement {
    sid       = "BedrockInvokeSpecificModels"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-haiku-*",
      "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-*",
      "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-*",
    ]
  }

  statement {
    sid       = "ReadSpecificSecrets"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db_credentials[0].arn]
  }

  statement {
    sid       = "WriteOwnLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api[0].arn}:*", "${aws_cloudwatch_log_group.finops[0].arn}:*"]
  }

  statement {
    sid       = "PutCustomMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "api" {
  count = var.enable_aws ? 1 : 0

  name   = "${var.project}-api-policy"
  role   = aws_iam_role.api[0].id
  policy = data.aws_iam_policy_document.api_policy[0].json
}

# Scheduler role: invoke ONLY the finops function.
data "aws_iam_policy_document" "scheduler_assume" {
  count = var.enable_aws ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "finops_scheduler" {
  count = var.enable_aws ? 1 : 0

  name               = "${var.project}-finops-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume[0].json

  tags = { Name = "${var.project}-finops-scheduler-role" }
}

resource "aws_iam_role_policy" "finops_scheduler" {
  count = var.enable_aws ? 1 : 0

  name = "${var.project}-finops-scheduler-policy"
  role = aws_iam_role.finops_scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.finops[0].arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count = var.enable_aws ? 1 : 0

  role       = aws_iam_role.api[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
