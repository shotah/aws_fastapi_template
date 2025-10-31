# Advanced Features Guide

This document explains the advanced production-ready features included in this template.

## Table of Contents
1. [Health Check Endpoint](#health-check-endpoint)
2. [Error Handling](#error-handling)
3. [Environment Configuration](#environment-configuration)
4. [Testing](#testing)

---

## Health Check Endpoint

### Overview
The `/health` endpoint provides service status information for monitoring systems and load balancers.

### Usage
```bash
curl https://your-api.com/health
```

### Response
```json
{
  "status": "healthy",
  "service": "AWS FastAPI Template",
  "version": "1.0.0",
  "environment": "dev",
  "timestamp": "2024-01-15T00:00:00Z",
  "checks": {
    "lambda": "ok"
  }
}
```

### Configuration in template.yaml
```yaml
Events:
  HealthCheck:
    Type: Api
    Properties:
      Path: /health
      Method: GET
```

### Extending Health Checks
Add dependency checks in `src/app.py`:
```python
"checks": {
    "lambda": "ok",
    "database": check_database_connection(),
    "cache": check_redis_connection(),
    "external_api": check_external_service()
}
```

---

## Error Handling

### Overview
Clean, production-ready error handling with proper HTTP status codes and detailed error responses.

### Architecture

#### 1. Custom Exception Classes (`src/exceptions.py`)
```python
from exceptions import NotFoundError, ValidationError, UnauthorizedError

# Raise custom exceptions in your code
raise NotFoundError(
    "User not found",
    resource_type="User",
    resource_id="123"
)
```

#### Available Exceptions
| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `ValidationError` | 400 | Invalid input validation |
| `UnauthorizedError` | 401 | Authentication failure |
| `ForbiddenError` | 403 | Authorization failure |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflict (duplicate) |
| `RateLimitError` | 429 | Rate limit exceeded |
| `ExternalServiceError` | 502 | External API failure |

#### 2. Exception Handlers (`src/app.py`)
```python
@app.exception_handler(AppException)
def handle_app_exception(ex: AppException) -> Response:
    """Automatically converts custom exceptions to HTTP responses."""
    return Response(
        status_code=ex.status_code,
        body={
            "error": ex.__class__.__name__,
            "message": ex.message,
            "details": ex.details
        }
    )
```

### Example Usage

#### In Your Endpoint
```python
@app.get("/users/<user_id>")
def get_user(user_id: str) -> dict[str, Any]:
    # Validate input
    if not user_id.isdigit():
        raise ValidationError(
            "Invalid user ID format",
            details={"user_id": user_id, "expected": "numeric"}
        )

    # Check if resource exists
    user = database.get_user(user_id)
    if not user:
        raise NotFoundError(
            f"User {user_id} not found",
            resource_type="User",
            resource_id=user_id
        )

    return user
```

#### Error Response (404)
```json
{
  "error": "NotFoundError",
  "message": "User 123 not found",
  "details": {
    "resource_type": "User",
    "resource_id": "123"
  }
}
```

#### Error Response (400)
```json
{
  "error": "ValidationError",
  "message": "Invalid user ID format",
  "details": {
    "user_id": "abc",
    "expected": "numeric"
  }
}
```

### Pydantic Validation Errors
Automatic 422 responses for invalid request bodies:
```json
{
  "error": "RequestValidationError",
  "message": "Request validation failed",
  "details": [
    {
      "type": "less_than_equal",
      "loc": ["body", "age"],
      "msg": "Input should be less than or equal to 150",
      "input": 200
    }
  ]
}
```

---

## Environment Configuration

### Overview
Type-safe configuration using Pydantic Settings with support for:
- `.env` files (local development)
- Environment variables (GitHub Actions, Lambda)
- AWS Secrets Manager (production)

### Setup

#### 1. Create `.env` file (local development)
```bash
cp env_variables.example .env
```

#### 2. Edit `.env`
```env
APP_NAME=My API
APP_VERSION=1.0.0
ENVIRONMENT=dev
LOG_LEVEL=DEBUG

# API Configuration
API_KEY=my-secret-key
MAX_REQUEST_SIZE=10485760

# AWS Resources
S3_BUCKET_NAME=my-bucket
DYNAMODB_TABLE_NAME=my-table

# Feature Flags
ENABLE_CORS=true
ENABLE_METRICS=true
```

### Usage in Code

#### Basic Usage
```python
from config import get_settings

settings = get_settings()

# Access configuration
print(settings.APP_NAME)  # "My API"
print(settings.LOG_LEVEL)  # "DEBUG"
print(settings.is_production())  # False
```

#### In Your Functions
```python
@app.get("/status")
def get_status():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }
```

### GitHub Actions

Set environment variables in your workflow:
```yaml
- name: Deploy
  env:
    ENVIRONMENT: prod
    LOG_LEVEL: INFO
    API_KEY: ${{ secrets.API_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: sam deploy
```

### AWS Secrets Manager

#### 1. Create Secret in AWS
```bash
aws secretsmanager create-secret \
  --name prod/myapp/config \
  --secret-string '{
    "DATABASE_URL": "postgresql://...",
    "JWT_SECRET": "your-secret-key",
    "API_KEY": "production-api-key"
  }'
```

#### 2. Set Environment Variable
```yaml
# template.yaml
Environment:
  Variables:
    AWS_SECRETS_NAME: prod/myapp/config
```

#### 3. Automatic Loading
Settings will automatically load from Secrets Manager on Lambda startup.

### Configuration Priority
1. AWS Secrets Manager (if `AWS_SECRETS_NAME` is set)
2. Environment variables
3. `.env` file
4. Default values

### Safe Logging
```python
# Mask sensitive values
safe_config = settings.model_dump_safe()
logger.info("Configuration loaded", extra={"config": safe_config})
# Output: {"API_KEY": "***REDACTED***", "DATABASE_URL": "***REDACTED***"}
```

### Adding New Settings
```python
# src/config.py
class Settings(BaseSettings):
    # Add your new setting
    MY_NEW_SETTING: str = Field(
        default="default_value",
        description="Description of what this does"
    )
```

---

## Testing

### Running Tests
```bash
# All tests
pipenv run pytest tests/ -v

# Specific test
pipenv run pytest tests/test_handler.py::test_health_check -v

# With coverage report
pipenv run pytest tests/ --cov-report html
```

### Test Structure

#### Health Check Test
```python
def test_health_check(base_apigw_event, lambda_context):
    base_apigw_event["path"] = "/health"

    ret = lambda_handler(base_apigw_event, lambda_context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert data["status"] == "healthy"
    assert "checks" in data
```

#### Error Handling Test
```python
def test_get_user_not_found(base_apigw_event, lambda_context):
    base_apigw_event["path"] = "/users/9999"
    base_apigw_event["pathParameters"] = {"user_id": "9999"}

    ret = lambda_handler(base_apigw_event, lambda_context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 404
    assert data["error"] == "NotFoundError"
    assert "not found" in data["message"]
```

### Coverage Requirements
- Minimum: 75%
- Current: 76%+

---

## Quick Reference

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/hello` | GET | Example endpoint |
| `/users` | POST | Create user |
| `/users/{id}` | GET | Get user by ID |

### HTTP Status Codes
| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Unprocessable | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server | Unexpected error |
| 502 | Bad Gateway | External service failed |

### Next Steps
1. Add authentication (API Key, JWT)
2. Implement database layer (DynamoDB)
3. Add CORS configuration
4. Set up CI/CD pipeline
5. Configure CloudWatch alarms
6. Add rate limiting
