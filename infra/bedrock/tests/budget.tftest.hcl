mock_provider "aws" {
  source = "./tests"
}
override_data {
  target = data.aws_caller_identity.current
  values = { account_id = "123456789012" }
}
override_data {
  target = data.aws_partition.current
  values = { partition = "aws" }
}
variables {
  trusted_principal_arn = "arn:aws:iam::123456789012:role/owner"
  budget_email          = "owner@example.com"
}
run "monthly_alerts" {
  command = plan
  assert {
    condition     = aws_budgets_budget.monthly.limit_amount == "5" && aws_budgets_budget.monthly.limit_unit == "USD" && aws_budgets_budget.monthly.time_unit == "MONTHLY" && aws_budgets_budget.monthly.budget_type == "COST"
    error_message = "Default budget must be USD 5 monthly cost."
  }
  assert {
    condition     = toset([for notice in aws_budgets_budget.monthly.notification : notice.threshold]) == toset([50, 80, 100]) && alltrue([for notice in aws_budgets_budget.monthly.notification : notice.comparison_operator == "GREATER_THAN" && notice.notification_type == "ACTUAL" && notice.threshold_type == "PERCENTAGE" && notice.subscriber_email_addresses == toset([var.budget_email])])
    error_message = "Require actual-cost email alerts at 50/80/100 percent."
  }
  assert {
    condition     = !aws_budgets_budget.monthly.cost_types[0].include_credit && !aws_budgets_budget.monthly.cost_types[0].include_refund && toset(one(aws_budgets_budget.monthly.cost_filter).values) == toset(local.budget_services)
    error_message = "Budget must aggregate application services before credits/refunds."
  }
}
run "zero_budget" {
  command = plan
  variables { monthly_budget_usd = 0 }
  expect_failures = [var.monthly_budget_usd]
}
run "negative_budget" {
  command = plan
  variables { monthly_budget_usd = -1 }
  expect_failures = [var.monthly_budget_usd]
}
run "missing_recipient" {
  command = plan
  variables { budget_email = "" }
  expect_failures = [var.budget_email]
}
run "invalid_recipient" {
  command = plan
  variables { budget_email = "invalid" }
  expect_failures = [var.budget_email]
}
