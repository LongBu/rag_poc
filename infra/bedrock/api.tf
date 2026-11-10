resource "aws_apigatewayv2_api" "chat" {
  name          = var.name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_authorizer" "owner" {
  api_id           = aws_apigatewayv2_api.chat.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "owner"
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.browser.id]
    issuer   = local.issuer
  }
}

resource "aws_apigatewayv2_integration" "chat" {
  api_id                 = aws_apigatewayv2_api.chat.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chat.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 26000
}

resource "aws_apigatewayv2_route" "query" {
  api_id               = aws_apigatewayv2_api.chat.id
  route_key            = "POST /query"
  target               = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type   = "JWT"
  authorizer_id        = aws_apigatewayv2_authorizer.owner.id
  authorization_scopes = ["chat/query"]
}

# Flask answers preflight without model/auth calls and emits CORS for the exact frontend origin.
resource "aws_apigatewayv2_route" "preflight" {
  api_id             = aws_apigatewayv2_api.chat.id
  route_key          = "OPTIONS /query"
  target             = "integrations/${aws_apigatewayv2_integration.chat.id}"
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "api" {
  for_each      = toset(["POST", "OPTIONS"])
  statement_id  = "Allow${each.key}Query"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chat.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.chat.execution_arn}/$default/${each.key}/query"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${var.name}"
  retention_in_days = 7
}

resource "aws_apigatewayv2_stage" "chat" {
  api_id      = aws_apigatewayv2_api.chat.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 2
    throttling_rate_limit  = 1
  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId = "$context.requestId"
      status    = "$context.status"
      latency   = "$context.responseLatency"
    })
  }
}
