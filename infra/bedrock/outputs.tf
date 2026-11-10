output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "region" {
  value = local.region
}

output "model_id" {
  value = local.model_id
}

output "cli_role_arn" {
  value = aws_iam_role.cli.arn
}

output "frontend_url" {
  value = local.frontend_origin
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}

output "user_pool_id" {
  value = aws_cognito_user_pool.owner.id
}

output "client_id" {
  value = aws_cognito_user_pool_client.browser.id
}

output "issuer" {
  value = local.issuer
}

output "login_origin" {
  value = local.login_origin
}

output "api_url" {
  value = aws_apigatewayv2_api.chat.api_endpoint
}

output "artifact_bucket" {
  value = aws_s3_bucket.artifacts.id
}

output "frontend_config" {
  description = "Public frontend config; contains no credentials."
  value = {
    apiUrl      = aws_apigatewayv2_api.chat.api_endpoint
    issuer      = local.issuer
    clientId    = aws_cognito_user_pool_client.browser.id
    loginOrigin = local.login_origin
    ownerSub    = var.owner_sub
  }
}
