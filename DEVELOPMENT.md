# Development Guide

Complete setup and deployment guide for the AWS Lambda SAM template.

## Table of Contents

- [Prerequisites & Installation](#prerequisites--installation)
- [Project Setup](#project-setup)
- [Environment Variables & Configuration](#environment-variables--configuration)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites & Installation

**Required Tools:**

- Python 3.13
- Make
- Pipenv
- AWS CLI
- AWS SAM CLI
- Docker

### Quick Install

<details>
<summary><b>Windows (Chocolatey)</b></summary>

```powershell
choco install python --version=3.13.8 --force
choco install make awscli awssamcli docker-desktop -y
pip install pipenv
```

</details>

<details>
<summary><b>macOS (Homebrew)</b></summary>

```bash
brew install python@3.13 awscli aws-sam-cli pipenv
brew install --cask docker
```

</details>

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

```bash
# Python 3.13
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip make docker.io

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# AWS SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation && sudo ./sam-installation/install

pip3 install pipenv
```

</details>

---

## Project Setup

```bash
# 1. Clone and install
git clone <your-repo-url>
cd aws_fastapi_template
make install-dev

# 2. Install pre-commit hooks
make hooks

# 3. Configure AWS credentials
aws configure

# 4. Verify setup
make test
```

---

## Environment Variables & Configuration

### Quick Reference: Choose Your Approach

| Use Case | Solution | Cost | Best For |
|----------|----------|------|----------|
| Local development | `env.json` | Free | Testing locally |
| Non-sensitive config | SAM Parameters | Free | Email, log levels, flags |
| Semi-sensitive | Parameter Store | Free | API endpoints, URLs |
| Highly sensitive | Secrets Manager | $0.40/mo | Passwords, API keys |

### 1. Local Development (`env.json`)

```bash
# Create from example
cp env.json.example env.json

# Edit with your values
{
  "HelloWorldFunction": {
    "LOG_LEVEL": "DEBUG",
    "API_KEY": "local-dev-key"
  }
}

# Automatically used by make start
```

### 2. AWS Deployment - SAM Parameters

**For non-sensitive values like emails, log levels**

Edit `samconfig.toml`:

```toml
[sandbox.deploy.parameters]
parameter_overrides = [
  "Environment=Sandbox",
  "LogLevel=DEBUG",
  "FromEmail=sandbox@example.com",
  "AdminEmail=admin@example.com"
]
# Optional: target specific AWS account
# profile = "sandbox"
# region = "us-east-1"
```

Deploy: `make deploy-sandbox`

### 3. AWS Secrets Manager

**For sensitive data (API keys, passwords, OAuth tokens)**

#### Setup AWS Profiles (Multi-Account)

**~/.aws/config** (uses `[profile name]` syntax):

```ini
[default]
region = us-east-1

[profile sandbox]
region = us-east-1

[profile prod]
region = us-east-1
```

**~/.aws/credentials** (no "profile" prefix):

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[sandbox]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[prod]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Key Difference:** Config uses `[profile name]`, credentials uses `[name]`

#### Common Commands

```bash
# Create secret
aws secretsmanager create-secret \
  --name /sandbox/my-app/api-key \
  --secret-string "your-secret" \
  --profile sandbox

# Update secret
aws secretsmanager update-secret \
  --secret-id /sandbox/my-app/api-key \
  --secret-string "new-value" \
  --profile sandbox

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id /sandbox/my-app/api-key \
  --query SecretString --output text \
  --profile sandbox

# List secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=/sandbox/ \
  --profile sandbox

# Delete secret
aws secretsmanager delete-secret \
  --secret-id /sandbox/my-app/api-key \
  --force-delete-without-recovery \
  --profile sandbox
```

**JSON Secrets:**

```bash
aws secretsmanager create-secret \
  --name /sandbox/my-app/config \
  --secret-string '{"api_key":"xxx","db_pass":"yyy"}' \
  --profile sandbox
```

#### Grant Lambda Access

In `template.yaml`:

```yaml
HelloWorldFunction:
  Type: AWS::Serverless::Function
  Properties:
    Policies:
      - AWSSecretsManagerGetSecretValuePolicy:
          SecretArn: !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:/${Environment}/my-app/*'
    Environment:
      Variables:
        API_KEY_SECRET: !Sub '/${Environment}/my-app/api-key'
```

#### Use in Lambda

Create `src/services/secrets.py`:

```python
"""AWS Secrets Manager helper."""
import json
from functools import lru_cache
import boto3

secrets_client = boto3.client('secretsmanager')

@lru_cache(maxsize=128)
def get_secret(secret_name: str):
    """Retrieve and cache secret from AWS Secrets Manager."""
    response = secrets_client.get_secret_value(SecretId=secret_name)
    try:
        return json.loads(response['SecretString'])
    except json.JSONDecodeError:
        return response['SecretString']
```

Use in `src/app.py`:

```python
import os
from services.secrets import get_secret

# Load at cold start (cached)
api_key = get_secret(os.environ['API_KEY_SECRET'])

@app.get("/hello")
def hello():
    # Use api_key
    return {"message": "Hello"}
```

### 4. AWS Parameter Store

**For non-sensitive config (cheaper than Secrets Manager)**

Same commands as Secrets Manager, replace `secretsmanager` with `ssm`:

```bash
# Create parameter
aws ssm put-parameter \
  --name /sandbox/my-app/api-endpoint \
  --value "https://api.example.com" \
  --type String \
  --profile sandbox

# Create encrypted parameter
aws ssm put-parameter \
  --name /sandbox/my-app/api-key \
  --value "secret-value" \
  --type SecureString \
  --profile sandbox

# Get parameter
aws ssm get-parameter \
  --name /sandbox/my-app/api-endpoint \
  --with-decryption \
  --query Parameter.Value --output text \
  --profile sandbox

# Get all parameters in path
aws ssm get-parameters-by-path \
  --path /sandbox/my-app/ \
  --with-decryption \
  --profile sandbox
```

#### Lambda Access

```yaml
HelloWorldFunction:
  Properties:
    Policies:
      - SSMParameterReadPolicy:
          ParameterName: !Sub '${Environment}/my-app/*'
```

Create `src/services/parameters.py`:

```python
"""Parameter Store helper."""
from functools import lru_cache
import boto3

ssm_client = boto3.client('ssm')

@lru_cache(maxsize=128)
def get_parameter(name: str, decrypt: bool = True) -> str:
    """Retrieve and cache parameter."""
    response = ssm_client.get_parameter(Name=name, WithDecryption=decrypt)
    return response['Parameter']['Value']
```

### Comparison: Secrets Manager vs Parameter Store

| Feature | Secrets Manager | Parameter Store |
|---------|----------------|-----------------|
| **Cost** | $0.40/secret/month | **Free** (Standard) |
| **Rotation** | Automatic | Manual |
| **Size Limit** | 65KB | 4KB (Standard) |
| **Best For** | Passwords, API keys | URLs, config values |

### Best Practices

1. **Naming:** Use `/{environment}/{app}/{purpose}` format
2. **Profiles:** Always use `--profile` flag for multi-account
3. **Caching:** Use `@lru_cache` to avoid repeated API calls
4. **Load Early:** Fetch secrets at Lambda cold start
5. **Verify Account:** Run `aws sts get-caller-identity --profile prod` before changes

---

## Development Workflow

### Common Commands

```bash
make help              # Show all commands
make lint              # Run linters (black, isort, flake8)
make test              # Run tests with coverage
make build             # Build Lambda in Docker
make start             # Start local API Gateway
```

### Local API Testing

```bash
# Start local API
make start

# Test endpoints
curl http://127.0.0.1:3000/health
curl http://127.0.0.1:3000/hello
curl -X POST http://127.0.0.1:3000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@example.com","age":30}'
```

### Available Endpoints

- `GET /health` - Health check
- `GET /hello` - Hello world example
- `GET /users/{id}` - Get user by ID
- `POST /users` - Create user
- `GET /files` - List files (S3)
- `POST /files` - Upload file (S3)

---

## Testing

```bash
# Run all tests
make test

# Run failed tests only
make test-failed

# Generate HTML coverage report
pipenv run pytest --cov=. --cov-report=html
```

### Mocking AWS Services

The template uses **[moto](https://github.com/getmoto/moto)** for AWS mocking.

Example test with S3:

```python
def test_upload_file(mock_s3_bucket, s3_client):
    """Test file upload (mocked - no AWS costs)."""
    from services.storage import get_storage_service

    service = get_storage_service()
    service.upload_file(b"Hello!", key="test.txt")

    # Verify using mocked client
    response = s3_client.get_object(Bucket=mock_s3_bucket, Key="test.txt")
    assert response["Body"].read() == b"Hello!"
```

Benefits: ✅ Fast ✅ Free ✅ Offline ✅ No AWS account needed

---

## Deployment

### Environment-Specific Deployments

```bash
# Sandbox (auto-confirm, DEBUG logs)
make deploy-sandbox

# Dev (auto-confirm, INFO logs)
make deploy-dev

# Production (manual confirm, WARNING logs)
make deploy-prod
```

### First Time Deployment

```bash
make deploy  # Interactive guided deployment
```

### Customize Environments

Edit `samconfig.toml`:

```toml
[dev.deploy.parameters]
parameter_overrides = [
  "Environment=Dev",
  "LogLevel=INFO",
  "FromEmail=dev@example.com"
]
# Target specific AWS account
# profile = "dev"
# region = "us-east-1"
```

### Destroy Environments

```bash
make destroy-sandbox  # Auto-confirm
make destroy-dev      # Auto-confirm
make destroy-prod     # Manual confirm required
```

### View Deployed Resources

After deployment, check:

- API Gateway endpoint (in output)
- [AWS Lambda Console](https://console.aws.amazon.com/lambda)
- [API Gateway Console](https://console.aws.amazon.com/apigateway)
- [CloudFormation Console](https://console.aws.amazon.com/cloudformation)

### Calling IAM-Protected APIs

```bash
# Using included script
make invoke-dev ENDPOINT=/hello
make invoke-prod ENDPOINT=/users/123

# Direct Python script
python scripts/call_api.py https://API_ID.execute-api.us-east-1.amazonaws.com/Prod/hello
python scripts/call_api.py https://API_ID.execute-api.us-east-1.amazonaws.com/Prod/users \
  -m POST -d '{"name":"John"}'
```

---

## Troubleshooting

<details>
<summary><b>AWS Credentials Not Found</b></summary>

```bash
aws configure
# Or verify current credentials
aws sts get-caller-identity
```

</details>

<details>
<summary><b>Docker Not Running</b></summary>

Start Docker Desktop and verify with `docker ps`
</details>

<details>
<summary><b>SAM Build Fails</b></summary>

```bash
make clean
make build
# Verify Docker is running
docker ps
```

</details>

<details>
<summary><b>Import Errors in Tests</b></summary>

Run tests from project root:

```bash
cd aws_fastapi_template
make test
```

</details>

<details>
<summary><b>Pre-commit Hooks Failing</b></summary>

```bash
make lint  # See detailed errors
pipenv run black .
pipenv run isort .
```

</details>

<details>
<summary><b>Python Version Issues</b></summary>

```bash
python --version  # Check version
pipenv --rm       # Remove old venv
pipenv --python 3.13
pipenv install --dev
```

</details>

---

## Project Structure

```
aws_fastapi_template/
├── src/                      # Lambda source
│   ├── app.py               # Routes
│   ├── decorators.py        # Response wrappers
│   ├── exceptions.py        # Error handling
│   ├── models.py            # Pydantic models
│   ├── helper.py            # Business logic
│   └── services/            # AWS integrations
│       ├── storage.py       # S3 service
│       ├── email.py         # SES service
│       ├── secrets.py       # Secrets Manager helper
│       └── parameters.py    # Parameter Store helper
├── tests/                   # Test files
│   ├── conftest.py          # Fixtures (AWS mocking)
│   ├── test_handler.py      # API tests
│   └── test_storage.py      # S3 tests
├── scripts/                 # Utility scripts
│   └── call_api.py          # IAM-authenticated API caller
├── events/                  # Sample events
├── template.yaml            # SAM/CloudFormation
├── samconfig.toml           # Multi-environment config
├── makefile                 # Build automation
└── env.json.example         # Local env template
```

---

## Code Quality

```bash
make lint  # Run all linters
```

**Configured tools:**

- black (formatter)
- isort (import organizer)
- flake8 (style guide)
- autopep8 (PEP 8 auto-fix)
- pyupgrade (syntax modernization)
- pre-commit hooks (auto-run on commit)

---

## CI/CD with GitHub Actions

<details>
<summary><b>Setup Instructions</b></summary>

1. Create `.github/workflows/deploy.yml`
2. Add GitHub secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `AWS_STACK_NAME`

**Better:** Use OIDC (no long-lived credentials):

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
    aws-region: us-east-1
```

See [AWS OIDC Guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
</details>

---

## Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Powertools](https://awslabs.github.io/aws-lambda-powertools-python/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)

---

## Getting Help

1. Check [AWS SAM CLI Issues](https://github.com/aws/aws-sam-cli/issues)
2. Review [AWS Lambda Docs](https://docs.aws.amazon.com/lambda/)
3. Open an issue in this repository

---

**Happy coding! 🚀**
