# API Client Scripts

This directory contains helper scripts for interacting with deployed API Gateway endpoints.

## `call_api.py` - IAM-Authenticated API Client

A Python script that makes AWS SigV4 signed requests to API Gateway endpoints that require IAM authorization. Configuration is managed through a `.env` file for easy repeatability.

### Features

- ✅ Configuration via `.env` file (easy to version control and share)
- ✅ Automatic AWS credential detection (uses your AWS CLI profile, IAM role, etc.)
- ✅ Automatic region detection from API URL
- ✅ Support for all HTTP methods (GET, POST, PUT, DELETE, etc.)
- ✅ JSON request/response handling
- ✅ Pretty-printed output

### Installation

Install the required dependencies:

```bash
pipenv install
```

### Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API details:**
   ```bash
   # .env
   API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/hello
   API_METHOD=GET
   API_DATA=
   ```

3. **Run the script:**
   ```bash
   python scripts/call_api.py
   ```

### Usage Examples

#### GET Request

```bash
# Edit .env
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/health
API_METHOD=GET
API_DATA=

# Run
python scripts/call_api.py
```

#### GET with Path Parameters

```bash
# .env
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/users/123
API_METHOD=GET
API_DATA=
```

#### POST Request

```bash
# .env
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/users
API_METHOD=POST
API_DATA={"name":"John Doe","email":"john@example.com","age":30}
```

#### File Upload (Base64)

```bash
# .env
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/files
API_METHOD=POST
API_DATA={"file_name":"test.txt","content":"SGVsbG8gV29ybGQh","content_type":"text/plain"}
```

#### DELETE Request

```bash
# .env
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/Dev/users/123
API_METHOD=DELETE
API_DATA=
```

### Why `.env` Instead of CLI Args?

**Repeatability & Speed:**
- Edit one file to test different endpoints
- No need to reconstruct long CLI commands
- Easy to switch between different test scenarios
- Can commit `.env.example` with common test cases
- Quick iteration during development

**Example workflow:**
```bash
# Test health check
vim .env  # Change URL to /health
python scripts/call_api.py

# Test user creation
vim .env  # Change to POST /users with data
python scripts/call_api.py

# Test same request again
python scripts/call_api.py  # No changes needed!
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

### Configuration Options

All configuration is done in the `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | ✅ Yes | - | Full API Gateway endpoint URL |
| `API_METHOD` | No | `GET` | HTTP method (GET, POST, PUT, DELETE, etc.) |
| `API_DATA` | No | - | JSON string for request body (POST/PUT/PATCH) |
| `API_TIMEOUT` | No | `30` | Request timeout in seconds |

### Example Output

```bash
$ python scripts/call_api.py

🔐 Making signed GET request to:
   https://abc123.execute-api.us-east-1.amazonaws.com/Dev/hello

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

**"API_URL not set in .env file"**
- Copy `.env.example` to `.env`
- Set `API_URL` to your API Gateway endpoint
- See `.env.example` for examples

**"No AWS credentials found!"**
- Run `aws configure` to set up credentials
- Or set `AWS_PROFILE` in your `.env` or environment
- Or ensure your IAM role is properly attached (if on AWS service)

**"Invalid JSON data"**
- Check your `API_DATA` is valid JSON
- Make sure to escape quotes properly in the .env file
- Use online JSON validator if needed

**"403 Forbidden"**
- Your IAM user/role lacks `execute-api:Invoke` permission
- Add the required policy to your IAM user/role

### Advanced: Multiple .env Files

You can maintain multiple `.env` files for different environments:

```bash
# .env.dev
API_URL=https://abc.execute-api.us-east-1.amazonaws.com/Dev/hello

# .env.prod
API_URL=https://xyz.execute-api.us-east-1.amazonaws.com/Prod/hello

# Switch environments by copying
cp .env.dev .env
python scripts/call_api.py

cp .env.prod .env
python scripts/call_api.py
```

## Future Scripts

This directory can hold additional helper scripts, such as:
- `generate_test_data.py` - Generate sample data for testing
- `load_test.py` - Run load tests against the API
- `migrate_data.py` - Data migration utilities
