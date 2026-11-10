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
run "private_hosting_and_login" {
  command = apply
  assert {
    condition     = aws_cognito_user_pool.owner.user_pool_tier == "LITE" && aws_cognito_user_pool.owner.admin_create_user_config[0].allow_admin_create_user_only
    error_message = "Only administrators may create users in the Lite pool."
  }
  assert {
    condition     = !aws_cognito_user_pool_client.browser.generate_secret && aws_cognito_user_pool_client.browser.allowed_oauth_flows == toset(["code"]) && contains(aws_cognito_user_pool_client.browser.allowed_oauth_scopes, "chat/query")
    error_message = "The browser must use code flow with a public client and query scope."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.frontend.block_public_acls && aws_s3_bucket_public_access_block.frontend.block_public_policy && aws_s3_bucket_public_access_block.frontend.ignore_public_acls && aws_s3_bucket_public_access_block.frontend.restrict_public_buckets
    error_message = "Frontend S3 must block all public access."
  }
  assert {
    condition     = aws_cloudfront_origin_access_control.frontend.signing_behavior == "always" && aws_cloudfront_origin_access_control.frontend.signing_protocol == "sigv4"
    error_message = "CloudFront must sign origin requests."
  }
  assert {
    condition     = aws_cloudfront_distribution.frontend.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https" && length(aws_cloudfront_distribution.frontend.logging_config) == 0
    error_message = "Require HTTPS and keep callback-bearing access logs disabled."
  }
  assert {
    condition     = aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].referrer_policy[0].referrer_policy == "no-referrer" && aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].content_type_options[0].override
    error_message = "Require no-referrer and nosniff headers."
  }
  assert {
    condition     = aws_cognito_user_pool_client.browser.callback_urls == toset(["${local.frontend_origin}/"]) && aws_cognito_user_pool_client.browser.logout_urls == toset(["${local.frontend_origin}/"])
    error_message = "Only exact application root callback/logout URLs may be used."
  }
  assert {
    condition     = alltrue([for directive in ["script-src 'self'", "base-uri 'none'", "object-src 'none'", "frame-ancestors 'none'", aws_apigatewayv2_api.chat.api_endpoint, local.issuer, local.login_origin] : strcontains(aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].content_security_policy[0].content_security_policy, directive)]) && !strcontains(aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].content_security_policy[0].content_security_policy, "unsafe-") && aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].content_security_policy[0].override
    error_message = "CSP must restrict scripts and connections and block objects/framing/base changes."
  }
  assert {
    condition     = strcontains(aws_cloudfront_response_headers_policy.frontend.security_headers_config[0].content_security_policy[0].content_security_policy, "${local.issuer}/ ")
    error_message = "CSP must allow issuer child paths, including /.well-known/openid-configuration."
  }
  assert {
    condition     = one(data.aws_iam_policy_document.frontend.statement).actions == toset(["s3:GetObject"]) && one(one(data.aws_iam_policy_document.frontend.statement).principals).identifiers == toset(["cloudfront.amazonaws.com"]) && toset(one(one(data.aws_iam_policy_document.frontend.statement).condition).values) == toset([aws_cloudfront_distribution.frontend.arn])
    error_message = "Only this CloudFront distribution may read frontend objects."
  }
}
