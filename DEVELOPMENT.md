# Development Guide

This guide will help you set up your development environment for working with this AWS Lambda SAM template.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Project Setup](#project-setup)
- [Common Workflows](#common-workflows)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, you'll need to install the following tools:

- **Python 3.13** - The runtime for this Lambda function
- **Make** - Build automation tool
- **Pipenv** - Python dependency management
- **AWS CLI** - For AWS credentials and deployment
- **AWS SAM CLI** - For building and testing Lambda functions locally
- **Docker** - Required for SAM local testing

## Installation

### Windows

Using [Chocolatey](https://chocolatey.org/) package manager:

```powershell
# Install Python 3.13
choco install python --version=3.13.8 --force

# Install Make
choco install make

# Install AWS CLI
choco install awscli -y

# Install AWS SAM CLI
choco install awssamcli -y

# Install Docker Desktop
choco install docker-desktop -y

# Install Pipenv
pip install pipenv

# Verify installations
python --version        # Should show Python 3.13.x
make --version
aws --version
sam --version
docker --version
pipenv --version
```

**Note:** You may need to restart your terminal after installation.

### macOS

Using [Homebrew](https://brew.sh/) package manager:

```bash
# Install Python 3.13
brew install python@3.13

# Make is pre-installed on macOS
# If needed: xcode-select --install

# Install AWS CLI
brew install awscli

# Install AWS SAM CLI
brew install aws-sam-cli

# Install Docker Desktop
brew install --cask docker

# Install Pipenv
brew install pipenv

# Verify installations
python3.13 --version
make --version
aws --version
sam --version
docker --version
pipenv --version
```

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.13
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip

# Install Make (usually pre-installed)
sudo apt install -y make

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install AWS SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Install Docker
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Pipenv
pip3 install pipenv

# Log out and back in for Docker group changes to take effect
```

## Project Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd aws_fastapi_template
   ```

2. **Install dependencies:**
   ```bash
   make install-dev
   ```
   This will:
   - Create a virtual environment using Pipenv
   - Install all Python dependencies (including dev tools)

3. **Install pre-commit hooks:**
   ```bash
   make hooks
   ```
   This installs git hooks that automatically run linters before each commit.

4. **Configure AWS credentials:**
   ```bash
   aws configure
   ```
   You'll be prompted for:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., `us-east-1`)
   - Default output format (use `json`)

5. **Verify your setup:**
   ```bash
   make aws-check   # Check AWS credentials
   make test        # Run tests
   ```

## Environment Variables

This project supports environment variables for both local development and production deployment.

### Local Development (env.json)

For local testing with `sam local`, you can use an `env.json` file:

1. **Create your local environment file:**
   ```bash
   cp env.json.example env.json
   ```

2. **Edit `env.json` with your values:**
   ```json
   {
     "HelloWorldFunction": {
       "LOG_LEVEL": "DEBUG",
       "API_KEY": "your-local-api-key",
       "DATABASE_URL": "http://localhost:5432"
     }
   }
   ```

3. **The file is automatically used by `make start`:**
   ```bash
   make start
   ```

**Note:** `env.json` is in `.gitignore` and will never be committed. Always use `env.json.example` for documentation.

### Production Deployment (template.yaml)

Environment variables for deployed Lambda functions are defined in `template.yaml`:

```yaml
Resources:
  HelloWorldFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          POWERTOOLS_SERVICE_NAME: PowertoolsHelloWorld
          POWERTOOLS_METRICS_NAMESPACE: Powertools
          LOG_LEVEL: INFO
          # Add your custom variables here:
          API_KEY: !Ref ApiKeyParameter
          DATABASE_URL: !Sub "https://${DatabaseEndpoint}"
```

#### Option 1: Hard-code values (not recommended for secrets)

```yaml
Environment:
  Variables:
    MY_VAR: "my-value"
```

#### Option 2: Use Parameters (better for deployment-time values)

Add to your `template.yaml`:

```yaml
Parameters:
  ApiKey:
    Type: String
    Description: API Key for external service
    NoEcho: true  # Hides value in CloudFormation console

Resources:
  HelloWorldFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          API_KEY: !Ref ApiKey
```

Then deploy with:
```bash
sam deploy --parameter-overrides ApiKey=your-secret-key
```

#### Option 3: Use AWS Secrets Manager (best for sensitive data)

1. **Create a secret in AWS Secrets Manager:**
   ```bash
   aws secretsmanager create-secret \
     --name my-app/api-key \
     --secret-string "your-secret-value"
   ```

2. **Grant Lambda permission in `template.yaml`:**
   ```yaml
   Resources:
     HelloWorldFunction:
       Type: AWS::Serverless::Function
       Properties:
         Policies:
           - AWSSecretsManagerGetSecretValuePolicy:
               SecretArn: !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:my-app/*'
         Environment:
           Variables:
             SECRET_NAME: my-app/api-key
   ```

3. **Retrieve in your Lambda code:**
   ```python
   import boto3
   import json
   import os

   def get_secret(secret_name):
       client = boto3.client('secretsmanager')
       response = client.get_secret_value(SecretId=secret_name)
       return json.loads(response['SecretString'])

   # In your Lambda handler
   api_key = get_secret(os.environ['SECRET_NAME'])
   ```

#### Option 4: Use AWS Systems Manager Parameter Store (good for non-sensitive config)

1. **Create a parameter:**
   ```bash
   aws ssm put-parameter \
     --name /my-app/config/endpoint \
     --value "https://api.example.com" \
     --type String
   ```

2. **Grant Lambda permission in `template.yaml`:**
   ```yaml
   Resources:
     HelloWorldFunction:
       Type: AWS::Serverless::Function
       Properties:
         Policies:
           - SSMParameterReadPolicy:
               ParameterName: my-app/config/*
   ```

3. **Retrieve in your Lambda code:**
   ```python
   import boto3

   def get_parameter(parameter_name):
       ssm = boto3.client('ssm')
       response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
       return response['Parameter']['Value']

   # In your Lambda handler
   endpoint = get_parameter('/my-app/config/endpoint')
   ```

### Environment Variables Reference

Current environment variables used by this template:

| Variable | Local (env.json) | Production (template.yaml) | Description |
|----------|------------------|----------------------------|-------------|
| `POWERTOOLS_SERVICE_NAME` | Optional | ✓ Set | Service name for Powertools logging |
| `POWERTOOLS_METRICS_NAMESPACE` | Optional | ✓ Set | Namespace for CloudWatch metrics |
| `LOG_LEVEL` | Optional | ✓ Set | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Common Workflows

### View Available Commands

```bash
make help
```

Or simply:
```bash
make
```

### Development Cycle

```bash
# 1. Make code changes
# Edit files in src/

# 2. Run linters
make lint

# 3. Run tests
make test

# 4. Test locally
make start
# Then visit: http://127.0.0.1:3000/hello

# 5. Invoke function directly
make invoke
```

### Running the API Locally

```bash
# Build and start local API Gateway
make start
```

This will:
- Build your Lambda function in a Docker container
- Start a local API Gateway on `http://127.0.0.1:3000`
- Hot-reload your code changes (after rebuild)

**Available Endpoints:**
- `GET http://127.0.0.1:3000/health` - Health check endpoint
- `GET http://127.0.0.1:3000/hello` - Hello World example (uses helper module)
- `POST http://127.0.0.1:3000/users` - Create user (demonstrates Pydantic validation)
- `GET http://127.0.0.1:3000/users/{id}` - Get user by ID (demonstrates error handling)

**Test with curl:**
```bash
# Health check
curl http://127.0.0.1:3000/health

# Hello endpoint
curl http://127.0.0.1:3000/hello

# Create user
curl -X POST http://127.0.0.1:3000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "age": 30}'

# Get user
curl http://127.0.0.1:3000/users/1000
```

To stop the server, press `Ctrl+C`.

---

## API Gateway Authorization

The template supports multiple authorization strategies. **AWS IAM authorization is recommended for enterprise/service-to-service communication.**

### Option 1: AWS IAM Authorization (Recommended)

Requires AWS SigV4 signed requests using IAM credentials. Best for:
- Service-to-service communication
- Pre-existing IAM roles/policies
- AWS SDK clients (boto3, AWS CLI, etc.)

#### Enable IAM Authorization

In `template.yaml`, uncomment the Auth section for any endpoint:

```yaml
Events:
  HelloPath:
    Type: Api
    Properties:
      Path: /hello
      Method: GET
      Auth:
        Authorizer: AWS_IAM  # Add this line
```

#### Required IAM Policy

Clients need an IAM policy attached to their user/role:

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

**Examples:**
```
All endpoints:     arn:aws:execute-api:us-east-1:123456789012:abc123xyz/Prod/*/*
Specific endpoint: arn:aws:execute-api:us-east-1:123456789012:abc123xyz/Prod/GET/hello
Users paths:       arn:aws:execute-api:us-east-1:123456789012:abc123xyz/Prod/*/users/*
```

#### Calling IAM-Protected APIs

**Using the included helper script (Recommended):**
```bash
# Install the required package first
pipenv install

# Call API using Makefile (automatically fetches API URL)
make invoke-dev                          # Calls /hello on dev
make invoke-dev ENDPOINT=/health         # Calls /health on dev
make invoke-dev ENDPOINT=/users/123      # Calls /users/123 on dev

# Or call directly with Python script (GET is default)
python scripts/call_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/hello
python scripts/call_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/users/123

# POST with JSON body (use --method and --data flags)
python scripts/call_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/users \
  --method POST --data '{"name":"John","email":"john@example.com"}'

# Short flags work too
python scripts/call_api.py https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/users \
  -m POST -d '{"name":"John","email":"john@example.com"}'

# Get full help
python scripts/call_api.py --help
```

**From your own Python code:**
```python
from requests_aws4auth import AWS4Auth
import requests
import boto3

# Get AWS credentials
session = boto3.Session()
credentials = session.get_credentials()

# Create AWS SigV4 auth
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    'us-east-1',
    'execute-api',
    session_token=credentials.token
)

# Make request
api_url = 'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/hello'
response = requests.get(api_url, auth=auth)
```

**From AWS CLI:**
```bash
aws apigatewayv2 invoke \
  --api-id abc123xyz \
  --stage Prod \
  --path /hello \
  output.json
```

**From Another Lambda:**
```python
# The Lambda execution role needs execute-api:Invoke permission
from aws_requests_auth.aws_auth import AWSRequestsAuth
import requests
import os

auth = AWSRequestsAuth(
    aws_access_key=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    aws_token=os.environ['AWS_SESSION_TOKEN'],
    aws_host='abc123xyz.execute-api.us-east-1.amazonaws.com',
    aws_region='us-east-1',
    aws_service='execute-api'
)

response = requests.get('https://...', auth=auth)
```

### Other Authorization Options

See `template.yaml` (lines 59-116) for detailed examples of:
- **Option 2:** Lambda Authorizer (Custom JWT/OAuth validation)
- **Option 3:** API Keys (Simple rate limiting)
- **Option 4:** Cognito User Pools (AWS managed user auth)

---

## Testing

### Run All Tests

```bash
make test
```

This runs pytest with coverage reporting. Minimum coverage threshold is 75%.

### Mocking AWS Services (S3, DynamoDB, etc.)

This template uses **[moto](https://github.com/getmoto/moto)** for mocking AWS services in tests. This allows you to test AWS integrations locally without incurring costs or requiring real AWS resources.

#### S3 Mocking Example

The template includes a fully working S3 integration example in `src/services/storage.py` with comprehensive tests in `tests/test_storage.py`.

**Reusable Fixtures (tests/conftest.py):**

```python
@pytest.fixture(scope="function")
def aws_credentials() -> None:
    """Set fake AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """Create a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture(scope="function")
def mock_s3_bucket(s3_client) -> str:
    """Create a mock S3 bucket for testing."""
    bucket_name = "test-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    os.environ["DATA_BUCKET"] = bucket_name
    return bucket_name
```

**Using in Tests:**

```python
from services.storage import get_storage_service

def test_upload_file(mock_s3_bucket, s3_client):
    """Test uploading a file to S3."""
    service = get_storage_service()

    # Upload file (mocked - no real S3 access)
    service.upload_file(
        file_content=b"Hello, World!",
        key="test/file.txt",
        content_type="text/plain"
    )

    # Verify using mocked S3 client
    response = s3_client.get_object(Bucket=mock_s3_bucket, Key="test/file.txt")
    assert response["Body"].read() == b"Hello, World!"
```

**Key Benefits:**
- ✅ Fast tests (no network calls)
- ✅ No AWS costs
- ✅ Deterministic behavior
- ✅ Works offline
- ✅ Automatic cleanup after each test

**Adding More AWS Service Mocks:**

To mock other AWS services (DynamoDB, SQS, SNS, etc.):

1. Add the service to `Pipfile`:
   ```toml
   moto = {extras = ["s3", "dynamodb", "sqs"], version = "*"}
   ```

2. Create fixtures in `conftest.py`:
   ```python
   @pytest.fixture
   def dynamodb_table(aws_credentials):
       with mock_aws():
           client = boto3.client("dynamodb", region_name="us-east-1")
           client.create_table(
               TableName="test-table",
               KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
               AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
               BillingMode="PAY_PER_REQUEST"
           )
           yield client
   ```

3. Use in your tests:
   ```python
   def test_dynamodb(dynamodb_table):
       # All DynamoDB operations are mocked
       dynamodb_table.put_item(TableName="test-table", Item={"id": {"S": "123"}})
   ```

### Run Only Failed Tests

```bash
make test-failed
```

### Run Specific Tests

```bash
pipenv run pytest tests/test_handler.py::test_lambda_handler -v
```

### Coverage Report

Coverage reports are automatically generated when running tests. To see detailed HTML report:

```bash
pipenv run pytest --cov=. --cov-report=html
# Open htmlcov/index.html in your browser
```

## Deployment

### First Time Deployment

```bash
make deploy
```

This will:
1. Check your AWS credentials
2. Build the application
3. Guide you through deployment with prompts
4. Create a CloudFormation stack
5. Deploy your Lambda function and API Gateway

You'll be asked to provide:
- Stack name (e.g., `my-lambda-api`)
- AWS Region
- Deployment bucket (created automatically)
- Confirmation prompts

### Subsequent Deployments

After first deployment, you can use the saved configuration:

```bash
make deploy
```

Or for CI/CD (no prompts):

```bash
make deploy-ci
```

### Environment-Specific Deployments

The template supports three pre-configured environments: **sandbox**, **dev**, and **prod**.

Each environment has its own configuration in `samconfig.toml` with different:
- Stack names (e.g., `aws-fastapi-template-sandbox`, `aws-fastapi-template-dev`)
- Environment parameters (`Environment=dev`, `LogLevel=INFO`)
- Confirmation settings (prod requires manual confirmation)
- Optional AWS profiles and regions

#### Deploy to Sandbox

```bash
make deploy-sandbox
# Automatically confirms, uses LogLevel=DEBUG
```

#### Deploy to Dev

```bash
make deploy-dev
# Automatically confirms, uses LogLevel=INFO
```

#### Deploy to Production

```bash
make deploy-prod
# ⚠️ REQUIRES manual confirmation
# Uses LogLevel=WARNING and production tags
```

#### Customize Environments

Edit `samconfig.toml` to customize each environment:

```toml
[dev.deploy.parameters]
parameter_overrides = [
  "Environment=dev",
  "LogLevel=INFO"
  # Add custom parameters:
  # "LambdaExecutionRoleArn=arn:aws:iam::123456789012:role/dev-lambda-role"
]
# Specify AWS profile and region:
# region = "us-east-1"
# profile = "dev-profile"
```

#### Manual Deployment (Advanced)

You can also deploy manually with custom config:

```bash
sam build
sam deploy --config-env sandbox --parameter-overrides "LogLevel=DEBUG"
```

### Destroying Environments

When you need to tear down an environment and delete all associated AWS resources:

#### Destroy Sandbox

```bash
make destroy-sandbox
# Automatically confirms and deletes all sandbox resources
```

#### Destroy Dev

```bash
make destroy-dev
# Automatically confirms and deletes all dev resources
```

#### Destroy Production

```bash
make destroy-prod
# ⚠️ REQUIRES manual confirmation
# Shows list of resources to be deleted before proceeding
```

**What gets deleted:**
- Lambda function(s)
- API Gateway REST API
- CloudWatch Log Groups
- CloudWatch Alarms
- IAM roles (if created by SAM)
- S3 deployment bucket (optionally, with `--s3-bucket` flag)

**Manual deletion:**
```bash
# Delete stack and S3 bucket
sam delete --stack-name aws-fastapi-template-dev --no-prompts --s3-bucket your-bucket-name
```

### View Deployed Resources

After deployment, the output will show:
- API Gateway endpoint URL
- Lambda function ARN
- CloudFormation stack name

You can also view resources in the AWS Console:
- [Lambda Functions](https://console.aws.amazon.com/lambda)
- [API Gateway](https://console.aws.amazon.com/apigateway)
- [CloudFormation](https://console.aws.amazon.com/cloudformation)

## Code Quality Tools

This project uses several tools to maintain code quality via **pre-commit hooks**:

### Linters & Formatters

- **black** - Opinionated code formatter (88 character line length)
- **isort** - Import statement organizer
- **flake8** - Style guide enforcement with complexity checks
- **autopep8** - PEP 8 auto-formatter
- **pyupgrade** - Automatic Python syntax modernization (3.9+)
- **Pre-commit hooks** - YAML/JSON/TOML validation, trailing whitespace, end-of-file-fixer, etc.

Run all linters:
```bash
make lint  # Runs pre-commit on all files
```

### Pre-commit Hooks

Git hooks automatically run linters before each commit:

```bash
# Install hooks (done automatically with make install-dev)
make hooks

# Run hooks manually
pipenv run pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

## Project Structure

```
aws_fastapi_template/
├── src/                      # Lambda function source code
│   ├── __init__.py
│   ├── app.py               # Routes only (clean!)
│   ├── decorators.py        # @unified_response decorator
│   ├── exceptions.py        # Custom exceptions + handler registration
│   ├── models.py            # Pydantic request/response models
│   ├── helper.py            # Business logic & domain models
│   ├── services/            # AWS service integrations
│   │   ├── __init__.py
│   │   └── storage.py       # S3 storage service
│   └── requirements.txt     # Runtime dependencies
├── scripts/                 # Helper scripts
│   ├── call_api.py          # IAM-authenticated API client
│   └── README.md            # Scripts documentation
├── tests/                   # Test files
│   ├── __init__.py
│   ├── conftest.py          # Shared pytest fixtures (includes AWS mocking)
│   ├── test_handler.py      # API handler tests
│   ├── test_storage.py      # S3 storage service tests (mocked with moto)
│   └── fixtures/            # JSON event fixtures
│       └── apigw_hello_event.json
├── events/                  # Sample event payloads for local testing
│   └── hello.json           # API Gateway event
├── terraform/               # Infrastructure as Code (alternative to SAM)
│   ├── main.tf              # Note: This is an alternative IaC option
│   ├── lambda.tf            # You can use either SAM (template.yaml) OR Terraform
│   ├── api_gateway.tf       # Both are provided for flexibility
│   └── ... (other Terraform files)
├── .pre-commit-config.yaml  # Pre-commit hooks config
├── Pipfile                  # Development dependencies
├── Pipfile.lock             # Locked dependency versions
├── pyproject.toml           # Tool configurations (pytest, coverage)
├── template.yaml            # SAM/CloudFormation template
├── samconfig.toml           # SAM deployment config (multi-environment)
├── makefile                 # Build automation (deploy, test, invoke, etc.)
├── env.json.example         # Local environment variables template
├── README.md                # Project overview & quick start
└── DEVELOPMENT.md           # This file (detailed setup guide)
```

## Troubleshooting

### Python Version Issues

**Problem:** Wrong Python version being used

**Solution:**
```bash
# Check your Python version
python --version

# On Mac/Linux, you may need to specify python3.13
python3.13 --version

# Recreate virtual environment with correct version
pipenv --rm
pipenv --python 3.13
pipenv install --dev
```

### Docker Not Running

**Problem:** `Cannot connect to Docker daemon`

**Solution:**
- Start Docker Desktop
- Wait for it to fully initialize
- Run `docker ps` to verify it's working

### AWS Credentials Not Found

**Problem:** `Unable to locate credentials`

**Solution:**
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Verify credentials
make aws-check
```

### SAM Build Fails

**Problem:** Build errors or dependency issues

**Solution:**
```bash
# Clean and rebuild
make clean
make build

# Check Docker is running
docker ps

# Verify src/requirements.txt exists and is correct
cat src/requirements.txt
```

### Import Errors in Tests

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
The project is configured with `pythonpath = "."` in `pyproject.toml`. Ensure you're running tests from the project root:

```bash
# Run from project root
cd aws_fastapi_template
make test
```

### Pre-commit Hooks Failing

**Problem:** Hooks fail on commit

**Solution:**
```bash
# Run hooks manually to see detailed errors
make lint

# Auto-fix many issues
pipenv run black .
pipenv run isort .
pipenv run autopep8 -r -i .

# Then commit again
git add .
git commit -m "Your message"
```

### Windows Make Issues

**Problem:** `make: command not found`

**Solution:**
```powershell
# Install make via Chocolatey
choco install make

# Or use WSL (Windows Subsystem for Linux)
wsl --install

# Or run commands directly
pipenv run pytest
sam build
```

## CI/CD with GitHub Actions

This project is ready for automated deployment using GitHub Actions. Here's how to set it up:

### Setting Up GitHub Actions

1. **Create the workflow directory:**
   ```bash
   mkdir -p .github/workflows
   ```

2. **Create `.github/workflows/deploy.yml`:**

```yaml
name: Deploy to AWS

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install pipenv
          pipenv install --dev

      - name: Run linters
        run: |
          pipenv run pre-commit run --all-files

      - name: Run tests
        run: |
          pipenv run pytest --cov=. --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  deploy:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Set up AWS SAM
        uses: aws-actions/setup-sam@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Build SAM application
        run: sam build --use-container

      - name: Deploy SAM application
        run: |
          sam deploy \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset \
            --stack-name ${{ secrets.AWS_STACK_NAME }} \
            --capabilities CAPABILITY_IAM \
            --region ${{ secrets.AWS_REGION }}
```

### GitHub Secrets Configuration

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for deployment | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region to deploy to | `us-east-1` |
| `AWS_STACK_NAME` | CloudFormation stack name | `my-lambda-api` |

**Security Best Practice:** Use OIDC authentication instead of long-lived credentials. See [Using OIDC with GitHub Actions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html).

### Advanced: Using OIDC (Recommended)

OIDC is more secure than storing AWS credentials:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    role-session-name: GitHubActionsSession
    aws-region: us-east-1
```

To set up OIDC:

1. **Create an OIDC provider in AWS IAM:**
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. **Create an IAM role** with trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### Workflow Features

The provided workflow:

- ✅ **Runs tests on PRs** - Ensures code quality before merging
- ✅ **Lints code** - Runs pre-commit hooks automatically
- ✅ **Code coverage** - Uploads coverage reports to Codecov
- ✅ **Auto-deploys on main** - Deploys only after tests pass
- ✅ **Uses containers** - Builds Lambda in Docker for consistency

### Environment-Specific Deployments

For multiple environments (dev, staging, prod):

```yaml
deploy-dev:
  runs-on: ubuntu-latest
  needs: test
  if: github.ref == 'refs/heads/develop'
  environment: development
  steps:
    # ... same as above but with dev stack name

deploy-prod:
  runs-on: ubuntu-latest
  needs: test
  if: github.ref == 'refs/heads/main'
  environment: production
  steps:
    # ... same as above but with prod stack name
```

### Local Testing of GitHub Actions

Test your workflow locally with [act](https://github.com/nektos/act):

```bash
# Install act
choco install act-cli  # Windows
brew install act       # macOS

# Run the workflow locally
act push

# Run specific job
act -j test
```

### Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [GitHub Actions for AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/deploying-using-github.html)
- [AWS Lambda Powertools Python](https://awslabs.github.io/aws-lambda-powertools-python/)
- [Pipenv Documentation](https://pipenv.pypa.io/)
- [Black Code Style](https://black.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [AWS SAM CLI Issues](https://github.com/aws/aws-sam-cli/issues)
2. Review [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
3. Open an issue in this repository

## Contributing

1. Create a feature branch
2. Make your changes
3. Run `make lint` and `make test`
4. Commit your changes (pre-commit hooks will run)
5. Push and create a pull request

Happy coding! 🚀
