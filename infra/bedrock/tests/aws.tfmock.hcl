mock_data "aws_iam_policy_document" {
  defaults = {
    json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
  }
}
mock_resource "aws_iam_role" {
  defaults = { arn = "arn:aws:iam::123456789012:role/test" }
}
mock_resource "aws_lambda_function" {
  defaults = {
    arn        = "arn:aws:lambda:us-east-1:123456789012:function:test"
    invoke_arn = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:test/invocations"
  }
}
mock_resource "aws_cloudwatch_log_group" {
  defaults = { arn = "arn:aws:logs:us-east-1:123456789012:log-group:test" }
}
mock_resource "aws_apigatewayv2_api" {
  defaults = {
    api_endpoint  = "https://abc.execute-api.us-east-1.amazonaws.com"
    execution_arn = "arn:aws:execute-api:us-east-1:123456789012:abc"
  }
}
mock_resource "aws_cloudfront_distribution" {
  defaults = {
    arn         = "arn:aws:cloudfront::123456789012:distribution/TEST"
    domain_name = "example.cloudfront.net"
  }
}
mock_resource "aws_cognito_user_pool" {
  defaults = { id = "us-east-1_test" }
}
