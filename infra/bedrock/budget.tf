locals {
  # AWS Price List servicename attributes verified 2026-11-09; recheck deployed budget filters.
  budget_services = ["Amazon Bedrock", "AWS Lambda", "Amazon API Gateway", "Amazon Cognito", "Amazon Simple Storage Service", "Amazon CloudFront", "AmazonCloudWatch"]
}

resource "aws_budgets_budget" "monthly" {
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "Service"
    values = local.budget_services
  }
  cost_types {
    include_credit = false
    include_refund = false
  }
  dynamic "notification" {
    for_each = toset([50, 80, 100])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.budget_email]
    }
  }
}
