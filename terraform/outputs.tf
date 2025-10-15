output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.hello_world_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_deployment.hello_world_deployment.stage_name}/hello"
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.hello_world_function.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.hello_world_function.function_name
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.hello_world_api.id
}
