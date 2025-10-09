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
   - Create a virtual environment
   - Install all Python dependencies
   - Set up pre-commit hooks

3. **Configure AWS credentials:**
   ```bash
   aws configure
   ```
   You'll be prompted for:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., `us-east-1`)
   - Default output format (use `json`)

4. **Verify your setup:**
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

**Endpoints:**
- `GET http://127.0.0.1:3000/hello` - Hello World endpoint

To stop the server, press `Ctrl+C`.

## Testing

### Run All Tests

```bash
make test
```

This runs pytest with coverage reporting. Minimum coverage threshold is 80%.

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

This project uses several tools to maintain code quality:

### Linters

- **Black** - Code formatter (88 character line length)
- **isort** - Import statement organizer
- **Flake8** - Style guide enforcement with complexity checks
- **autopep8** - PEP 8 auto-formatter

Run all linters:
```bash
make lint
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
├── src/                    # Lambda function source code
│   ├── __init__.py
│   ├── app.py             # Main Lambda handler
│   └── requirements.txt   # Runtime dependencies
├── tests/                 # Test files
│   ├── __init__.py
│   └── test_handler.py    # Handler tests
├── events/                # Sample event payloads
│   └── hello.json         # API Gateway event
├── .vscode/               # VS Code settings
│   └── settings.json      # Black formatter config
├── .pre-commit-config.yaml # Pre-commit hooks config
├── Pipfile                # Development dependencies
├── pyproject.toml         # Tool configurations
├── template.yaml          # SAM/CloudFormation template
├── samconfig.toml         # SAM deployment config
├── makefile               # Build automation
└── DEVELOPMENT.md         # This file
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

## Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Powertools Python](https://awslabs.github.io/aws-lambda-powertools-python/)
- [Pipenv Documentation](https://pipenv.pypa.io/)
- [Black Code Style](https://black.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

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
