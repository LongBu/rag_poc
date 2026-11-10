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
run "bounded_protected_api" {
  command = apply
  assert {
    condition     = aws_apigatewayv2_route.query.route_key == "POST /query" && aws_apigatewayv2_route.query.authorization_type == "JWT" && aws_apigatewayv2_route.query.authorization_scopes == toset(["chat/query"])
    error_message = "Query must require a scoped JWT."
  }
  assert {
    condition     = aws_apigatewayv2_authorizer.owner.jwt_configuration[0].issuer == local.issuer && aws_apigatewayv2_authorizer.owner.jwt_configuration[0].audience == toset([aws_cognito_user_pool_client.browser.id])
    error_message = "JWT issuer and app client must match the configured pool."
  }
  assert {
    condition     = aws_lambda_function.chat.runtime == "python3.14" && toset(aws_lambda_function.chat.architectures) == toset(["x86_64"]) && aws_lambda_function.chat.timeout == 25 && aws_lambda_function.chat.reserved_concurrent_executions == 1 && length(aws_lambda_function.chat.vpc_config) == 0
    error_message = "Require Python 3.14, matching build architecture, bounded runtime/concurrency, and no VPC."
  }
  assert {
    condition     = aws_apigatewayv2_stage.chat.default_route_settings[0].throttling_rate_limit == 1 && aws_apigatewayv2_stage.chat.default_route_settings[0].throttling_burst_limit == 2
    error_message = "API request rate must be bounded."
  }
  assert {
    condition     = aws_lambda_permission.api["POST"].source_arn == "${aws_apigatewayv2_api.chat.execution_arn}/$default/POST/query" && aws_lambda_permission.api["OPTIONS"].source_arn == "${aws_apigatewayv2_api.chat.execution_arn}/$default/OPTIONS/query"
    error_message = "Lambda invocation must be scoped to the query routes only."
  }
  assert {
    condition     = aws_lambda_function.chat.environment[0].variables.FRONTEND_ORIGIN == local.frontend_origin && aws_lambda_function.chat.environment[0].variables.OWNER_SUB == "" && aws_apigatewayv2_route.preflight.route_key == "OPTIONS /query"
    error_message = "CORS must name the exact frontend origin and empty owner must fail closed."
  }
  assert {
    condition     = toset(keys(jsondecode(aws_apigatewayv2_stage.chat.access_log_settings[0].format))) == toset(["requestId", "status", "latency"]) && aws_cloudwatch_log_group.api.retention_in_days == 7
    error_message = "Access logs must contain only safe operational fields with finite retention."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.artifacts.block_public_acls && aws_s3_bucket_public_access_block.artifacts.block_public_policy && aws_s3_bucket_public_access_block.artifacts.ignore_public_acls && aws_s3_bucket_public_access_block.artifacts.restrict_public_buckets
    error_message = "Deployment artifacts must never be public."
  }
}
