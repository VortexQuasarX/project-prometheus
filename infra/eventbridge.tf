# -----------------------------------------------------------------------------
# EventBridge — FinOps agent triggers.
# 1. Daily 09:00 UTC scheduled review (costs ~$1/schedule/mo).
# 2. Reactive rule: budget alerts on the default bus invoke the FinOps agent.
# -----------------------------------------------------------------------------
resource "aws_scheduler_schedule" "finops_daily" {
  count = var.enable_aws ? 1 : 0

  name = "${var.project}-finops-daily"

  flexible_time_window {
    mode = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  schedule_expression = "cron(0 9 * * ? *)"
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_lambda_function.finops[0].arn
    role_arn = aws_iam_role.finops_scheduler[0].arn

    input = jsonencode({
      trigger    = "scheduled_finops_review"
      agent_type = "finops"
    })
  }
}

resource "aws_cloudwatch_event_rule" "budget_alert" {
  count = var.enable_aws ? 1 : 0

  name        = "${var.project}-budget-alert"
  description = "Invoke the FinOps agent when a budget alert is published"

  event_pattern = jsonencode({
    source      = ["prometheus.governance"]
    detail-type = ["Prometheus Budget Alert"]
  })

  tags = { Name = "${var.project}-budget-alert-rule" }
}

resource "aws_cloudwatch_event_target" "budget_alert_finops" {
  count = var.enable_aws ? 1 : 0

  rule = aws_cloudwatch_event_rule.budget_alert[0].name
  arn  = aws_lambda_function.finops[0].arn
}
