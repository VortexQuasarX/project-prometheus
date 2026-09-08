# -----------------------------------------------------------------------------
# CloudWatch — logs (7-day retention), a cost/ops dashboard, and two alarms.
# Free tier covers 3 dashboards and 10 custom metrics; stay under both.
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "aurora" {
  count = var.enable_aws ? 1 : 0

  name              = "/aws/rds/${var.project}-aurora"
  retention_in_days = 7

  tags = { Name = "${var.project}-aurora-logs" }
}

resource "aws_cloudwatch_dashboard" "overview" {
  count = var.enable_aws ? 1 : 0

  dashboard_name = "${var.project}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Estimated daily cost (custom metric)"
          region = var.aws_region
          metrics = [["prometheus", "cost_daily_usd"]]
          view    = "timeSeries"
          stat    = "Sum"
          period  = 3600
        }
      },
      {
        type = "metric"
        x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "API requests / cache hit rate"
          region = var.aws_region
          metrics = [["prometheus", "requests_total"], [".", "cache_hits"], [".", "cache_misses"]]
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
        }
      },
      {
        type = "metric"
        x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "Latency p95 (custom metric)"
          region = var.aws_region
          metrics = [["prometheus", "latency_p95_ms"]]
          view    = "timeSeries"
          stat    = "Maximum"
          period  = 300
        }
      },
      {
        type = "metric"
        x = 12, y = 6, width = 12, height = 6
        properties = {
          title  = "Kill switch state / eval pass rate"
          region = var.aws_region
          metrics = [["prometheus", "kill_switch_state"], [".", "eval_pass_rate"]]
          view    = "timeSeries"
          stat    = "Average"
          period  = 300
        }
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "budget_critical" {
  count = var.enable_aws ? 1 : 0

  alarm_name          = "${var.project}-budget-critical"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "cost_daily_usd"
  namespace           = "prometheus"
  period              = 3600
  statistic           = "Sum"
  threshold           = 2.0 # mirrors DAILY_BUDGET_USD
  alarm_description   = "Daily LLM spend reached the policy budget; expect the kill switch to escalate."

  tags = { Name = "${var.project}-budget-alarm" }
}

resource "aws_cloudwatch_metric_alarm" "error_spike" {
  count = var.enable_aws ? 1 : 0

  alarm_name          = "${var.project}-error-spike"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "errors_total"
  namespace           = "prometheus"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Spike of provider errors; check the dead-letter table."

  tags = { Name = "${var.project}-error-alarm" }
}
