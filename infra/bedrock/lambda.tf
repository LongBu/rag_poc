locals {
  lambda_zip = "${path.module}/../../backend/artifacts/lambda.zip"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.name}-artifacts-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "lambda" {
  bucket       = aws_s3_bucket.artifacts.id
  key          = "lambda/${filesha256(local.lambda_zip)}.zip"
  source       = local.lambda_zip
  source_hash  = filesha256(local.lambda_zip)
  content_type = "application/zip"
  depends_on   = [aws_s3_bucket_public_access_block.artifacts]
}

resource "aws_lambda_function" "chat" {
  function_name                  = var.name
  role                           = aws_iam_role.lambda.arn
  runtime                        = "python3.14"
  architectures                  = ["x86_64"]
  handler                        = "run.sh"
  s3_bucket                      = aws_s3_object.lambda.bucket
  s3_key                         = aws_s3_object.lambda.key
  source_code_hash               = filebase64sha256(local.lambda_zip)
  layers                         = ["arn:aws:lambda:us-east-1:753240598075:layer:LambdaAdapterLayerX86:30"]
  memory_size                    = 512
  timeout                        = 25
  reserved_concurrent_executions = 1
  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER                = "/opt/bootstrap"
      AWS_LWA_PORT                           = "8000"
      AWS_LWA_READINESS_CHECK_PATH           = "/ready"
      AWS_LWA_READINESS_CHECK_HEALTHY_STATUS = "200"
      AWS_LWA_INVOKE_MODE                    = "buffered"
      ISSUER                                 = local.issuer
      CLIENT_ID                              = aws_cognito_user_pool_client.browser.id
      OWNER_SUB                              = var.owner_sub
      FRONTEND_ORIGIN                        = local.frontend_origin
      LANGSMITH_TRACING                      = "false"
      LANGCHAIN_TRACING_V2                   = "false"
    }
  }
  depends_on = [aws_iam_role_policy.lambda_model, aws_iam_role_policy.lambda_logs]
}
