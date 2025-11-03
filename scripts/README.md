# API Client Scripts

This directory contains helper scripts for interacting with deployed API Gateway endpoints.

## `call_api.py` - IAM-Authenticated API Client

A Python script that makes AWS SigV4 signed requests to API Gateway endpoints that require IAM authorization.

### Features

- ✅ Automatic AWS credential detection (uses your AWS CLI profile, IAM role, etc.)
- ✅ Automatic region detection from API URL
- ✅ Support for all HTTP methods (GET, POST, PUT, DELETE, etc.)
- ✅ JSON request/response handling
- ✅ Pretty-printed output

### Installation

Install the required dependencies:

```bash
pip install requests requests-aws4auth boto3
# or
pipenv install requests-aws4auth
```

### Usage

#### Direct Usage

```bash
# GET request (default method)
python scripts/call_api.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/hello

# GET with path parameters
python scripts/call_api.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/users/123

# POST request with JSON body
python scripts/call_api.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/users \
  --method POST --data '{"name":"John","email":"john@example.com"}'

# Short flags
python scripts/call_api.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/users \
  -m POST -d '{"name":"John","email":"john@example.com"}'

# PUT request
python scripts/call_api.py https://api.../Prod/users/123 \
  --method PUT --data '{"name":"Jane"}'

# DELETE request
python scripts/call_api.py https://api.../Prod/users/123 --method DELETE

# Custom timeout (default: 30 seconds)
python scripts/call_api.py https://api.../Prod/slow-endpoint --timeout 60

# Get help
python scripts/call_api.py --help
```

#### Via Makefile (Recommended)

The Makefile provides convenient wrappers that automatically fetch your API URL:

```bash
# Default endpoint (/hello)
make invoke-dev

# Specific endpoint
make invoke-dev ENDPOINT=/health
make invoke-dev ENDPOINT=/users/123

# Different environments
make invoke-sandbox ENDPOINT=/hello
make invoke-prod ENDPOINT=/users/456

# Different HTTP methods (future support for POST data)
make invoke-dev ENDPOINT=/users METHOD=POST
```

### How It Works

1. **Fetches AWS Credentials**: Uses `boto3` to get your current AWS credentials
2. **Extracts Region**: Parses the API Gateway URL to determine the AWS region
3. **Signs Request**: Creates an AWS SigV4 signature using `requests-aws4auth`
4. **Makes Request**: Sends the signed request to API Gateway
5. **Displays Response**: Pretty-prints the JSON response

### Credential Sources (in order of precedence)

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
2. AWS CLI profile (via `AWS_PROFILE` env var or `~/.aws/credentials`)
3. IAM role (if running on EC2, Lambda, ECS, etc.)
4. Web identity token (for OIDC/SAML authentication)

### Required IAM Permissions

The AWS credentials you use must have the `execute-api:Invoke` permission:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:REGION:ACCOUNT_ID:API_ID/STAGE/METHOD/PATH"
    }
  ]
}
```

### Example Output

```bash
$ python scripts/call_api.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/hello

🔐 Making signed GET request to:
   https://abc123.execute-api.us-east-1.amazonaws.com/Prod/hello

📥 Response Status: 200
📥 Response Headers:
   content-type: application/json
   content-length: 142
   x-amzn-requestid: 12345678-1234-1234-1234-123456789012

📄 Response Body:
{
  "success": true,
  "data": {
    "message": "Hello from Lambda!",
    "timestamp": "2025-11-03T12:34:56.789Z"
  },
  "error": null
}
```

### Troubleshooting

**"No AWS credentials found!"**
- Run `aws configure` to set up credentials
- Or set `AWS_PROFILE` environment variable
- Or ensure your IAM role is properly attached (if on AWS service)

**"Error: Stack not found" (when using Makefile)**
- Deploy the stack first: `make deploy-dev`
- Check the stack name matches: `aws cloudformation list-stacks`

**"403 Forbidden"**
- Your IAM user/role lacks `execute-api:Invoke` permission
- Add the required policy to your IAM user/role

## Future Scripts

This directory can hold additional helper scripts, such as:
- `generate_test_data.py` - Generate sample data for testing
- `load_test.py` - Run load tests against the API
- `migrate_data.py` - Data migration utilities
