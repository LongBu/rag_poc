mock_provider "aws" {
  source = "./tests"
}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "123456789012"
  }
}

override_data {
  target = data.aws_partition.current
  values = {
    partition = "aws"
  }
}

variables {
  trusted_principal_arn = "arn:aws:iam::123456789012:role/owner"
  budget_email          = "owner@example.com"
}

run "scoped_identity" {
  command = plan
  assert {
    condition     = one(data.aws_iam_policy_document.model.statement).actions == toset(["bedrock:InvokeModel"])
    error_message = "Runtime policies must only allow non-streaming invocation."
  }
  assert {
    condition     = one(data.aws_iam_policy_document.model.statement).resources == toset(["arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0"])
    error_message = "Invocation must be scoped to the selected regional model."
  }
  assert {
    condition     = one(one(data.aws_iam_policy_document.cli_trust.statement).principals).identifiers == toset([var.trusted_principal_arn])
    error_message = "CLI trust must identify the configured caller only."
  }
  assert {
    condition     = one(one(data.aws_iam_policy_document.lambda_trust.statement).principals).identifiers == toset(["lambda.amazonaws.com"])
    error_message = "Lambda trust must be separate from CLI trust."
  }
  assert {
    condition     = one(data.aws_iam_policy_document.logs.statement).actions == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) && aws_cloudwatch_log_group.lambda.retention_in_days == 7
    error_message = "Logs must have bounded retention and write-only runtime permissions."
  }
}

run "reject_cross_account_trust" {
  command = plan
  variables {
    trusted_principal_arn = "arn:aws:iam::222222222222:role/other"
  }
  expect_failures = [aws_iam_role.cli]
}

run "reject_session_arn" {
  command = plan
  variables {
    trusted_principal_arn = "arn:aws:sts::123456789012:assumed-role/owner/session"
  }
  expect_failures = [var.trusted_principal_arn]
}
