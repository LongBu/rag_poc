resource "aws_cognito_user_pool" "owner" {
  name                     = var.name
  user_pool_tier           = "LITE"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 1
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_domain" "owner" {
  domain                = "${var.name}-${data.aws_caller_identity.current.account_id}"
  user_pool_id          = aws_cognito_user_pool.owner.id
  managed_login_version = 1
}

resource "aws_cognito_resource_server" "chat" {
  identifier   = "chat"
  name         = "Private chat"
  user_pool_id = aws_cognito_user_pool.owner.id
  scope {
    scope_name        = "query"
    scope_description = "Ask the private model"
  }
}

resource "aws_cognito_user_pool_client" "browser" {
  name                                 = "${var.name}-browser"
  user_pool_id                         = aws_cognito_user_pool.owner.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "${aws_cognito_resource_server.chat.identifier}/query"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["${local.frontend_origin}/"]
  logout_urls                          = ["${local.frontend_origin}/"]
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  access_token_validity                = 5
  id_token_validity                    = 5
  refresh_token_validity               = 1
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "hours"
  }
}

locals {
  issuer       = "https://cognito-idp.${local.region}.amazonaws.com/${aws_cognito_user_pool.owner.id}"
  login_origin = "https://${aws_cognito_user_pool_domain.owner.domain}.auth.${local.region}.amazoncognito.com"
}
