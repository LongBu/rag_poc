data "aws_iam_policy_document" "cli_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [var.trusted_principal_arn]
    }
  }
}

resource "aws_iam_role" "cli" {
  name               = "${var.name}-cli"
  assume_role_policy = data.aws_iam_policy_document.cli_trust.json
  lifecycle {
    precondition {
      condition     = split(":", var.trusted_principal_arn)[4] == data.aws_caller_identity.current.account_id
      error_message = "The trusted caller must belong to the deployment account."
    }
  }
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "model" {
  statement {
    actions   = ["bedrock:InvokeModel"]
    resources = [local.model_arn]
  }
}

resource "aws_iam_role_policy" "cli_model" {
  role   = aws_iam_role.cli.id
  policy = data.aws_iam_policy_document.model.json
}

resource "aws_iam_role_policy" "lambda_model" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.model.json
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 7
}

data "aws_iam_policy_document" "logs" {
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_logs" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.logs.json
}
