# Data source for Lambda zip file
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.lambda_src_path
  output_path = "${local.building_path}/${local.lambda_code_filename}"
  depends_on  = [null_resource.build_lambda_function]
}

# Build logic for Lambda function
resource "null_resource" "build_lambda_function" {
  triggers = {
    build_number = timestamp()
    requirements_hash = filemd5("../requirements.txt")
    source_hash = filemd5("../src/app.py")
  }

  provisioner "local-exec" {
    command = substr(pathexpand("~"), 0, 1) == "/" ?
      "./build_lambda.sh \"${local.lambda_src_path}\" \"${local.building_path}\" \"${local.lambda_code_filename}\"" :
      "powershell.exe -File .\\build_lambda.ps1 ${local.lambda_src_path} ${local.building_path} ${local.lambda_code_filename}"
  }
}

# SAM metadata resource for AWS SAM CLI integration
resource "null_resource" "sam_metadata_aws_lambda_function_hello_world_function" {
  triggers = {
    resource_name = "aws_lambda_function.hello_world_function"
    resource_type = "ZIP_LAMBDA_FUNCTION"
    original_source_code = local.lambda_src_path
    built_output_path = "${local.building_path}/${local.lambda_code_filename}"
  }

  depends_on = [
    null_resource.build_lambda_function
  ]
}
