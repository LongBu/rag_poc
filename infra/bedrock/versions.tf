terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { Project = var.name }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  region    = "us-east-1"
  model_id  = "amazon.nova-micro-v1:0"
  model_arn = "arn:${data.aws_partition.current.partition}:bedrock:${local.region}::foundation-model/${local.model_id}"
}
