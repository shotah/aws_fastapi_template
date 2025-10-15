# Resource Group for Application Insights
resource "aws_resourcegroups_group" "application_resource_group" {
  name = "ApplicationInsights-SAM-${local.stack_name}"

  resource_query {
    query = jsonencode({
      ResourceTypeFilters = ["AWS::CloudFormation::Stack"]
      TagFilters = [
        {
          Key    = "aws:cloudformation:stack-name"
          Values = [local.stack_name]
        }
      ]
    })
  }

  tags = {
    Name = "ApplicationInsights-SAM-${local.stack_name}"
    LambdaPowertools = "python"
  }
}

# Application Insights Application
resource "aws_applicationinsights_application" "application_insights_monitoring" {
  resource_group_name = aws_resourcegroups_group.application_resource_group.name
  auto_config_enabled = true

  tags = {
    Name = "${local.stack_name}-application-insights"
    LambdaPowertools = "python"
  }
}
