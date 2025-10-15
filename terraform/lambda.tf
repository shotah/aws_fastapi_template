# IAM role for Lambda function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${local.stack_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.stack_name}-lambda-execution-role"
    LambdaPowertools = "python"
  }
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "lambda_execution_policy" {
  name = "${local.stack_name}-lambda-execution-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "Powertools"
          }
        }
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "hello_world_function" {
  filename         = "${local.building_path}/${local.lambda_code_filename}"
  function_name    = "${local.stack_name}-HelloWorldFunction"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "app.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  architectures   = ["x86_64"]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      POWERTOOLS_SERVICE_NAME = "PowertoolsHelloWorld"
      POWERTOOLS_METRICS_NAMESPACE = "Powertools"
      LOG_LEVEL = var.log_level
    }
  }

  tags = {
    Name = "${local.stack_name}-HelloWorldFunction"
    LambdaPowertools = "python"
  }

  depends_on = [
    aws_iam_role_policy.lambda_execution_policy,
    aws_cloudwatch_log_group.lambda_log_group
  ]
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${local.stack_name}-HelloWorldFunction"
  retention_in_days = 14

  tags = {
    Name = "${local.stack_name}-lambda-log-group"
    LambdaPowertools = "python"
  }
}
