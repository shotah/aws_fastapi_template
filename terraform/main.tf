terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Local values for common paths and configurations
locals {
  lambda_src_path     = "../src"
  building_path       = "../build"
  lambda_code_filename = "lambda_function.zip"
  stack_name          = "AWS_FASTAPI_TEMPLATE"
}

# Data source for current AWS region
data "aws_region" "current" {}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
