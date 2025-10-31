# AWS Lambda + SAM + Powertools Template

A production-ready AWS Lambda template using SAM CLI, AWS Lambda Powertools, and modern Python best practices.

**Not just another "hello world" - this is how you build Lambda functions at scale.**

---

## 🎯 Why This Template?

Most Lambda templates show you the basics. This one shows you **the right way** - patterns you'd discover after building 10+ production Lambda functions.

### **Architectural Highlights**

#### **1. Clean Code Architecture**
- **`app.py`** = Routes only (no infrastructure noise)
- **`decorators.py`** = Reusable response wrappers
- **`exceptions.py`** = Centralized error handling with registration pattern
- **`models.py`** = Pydantic request/response contracts
- **`helper.py`** = Business logic & domain models

**Why?** At 2am when production is down, you want to scan routes, not wade through 2000 lines of mixed concerns.

#### **2. Unified Response Envelope**
Every endpoint returns a consistent structure:

```json
{
  "success": true,
  "data": { "your": "response" },
  "error": null
}
```

**Implementation:** One decorator (`@unified_response`) wraps all successful responses. Exception handler wraps all errors. Zero boilerplate in your routes.

**Why?** Frontend teams will love you. Monitoring becomes trivial. No more guessing response shapes.

#### **3. Pydantic Everywhere**
- **Request validation** - Automatic via Powertools + Pydantic
- **Response serialization** - Type-safe with `.model_dump()`
- **Domain models** - Business logic with validation
- **No raw dicts** - Everything is typed and validated

**Why?** Bugs caught at code time, not runtime. Clear contracts. Self-documenting APIs.

#### **4. Exception Handler Registration Pattern**
```python
# app.py - Clean!
register_exception_handlers(app)

# exceptions.py - All error handling logic
def register_exception_handlers(app):
    @app.exception_handler(AppException)
    def handle_app_exception(ex):
        return format_error_response(ex)
```

**Why?** As you scale to 10+ exception types, this pattern keeps `app.py` focused on business logic.

#### **5. Separation of API Models vs Domain Models**
- **API Models** (`models.py`) = Request/Response contracts
- **Domain Models** (`helper.py`) = Business entities

**Includes circular dependency solution** using `TYPE_CHECKING` and runtime imports.

**Why?** API contracts shouldn't dictate your domain design. Keep them separate, avoid duplication.

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.13+
- Docker (for SAM local testing)
- AWS SAM CLI
- Pipenv

### **Setup**
```bash
# Install dependencies
pipenv install --dev

# Build the Lambda function
make build

# Run locally (requires Docker)
make start

# Run tests
make test
```

### **Available Make Commands**
```bash
make build              # Build SAM application in Docker container
make build-no-container # Build without Docker (faster, less reliable)
make start              # Start local API Gateway
make test               # Run pytest with coverage
make lint               # Run linters (ruff, mypy)
make clean              # Clean build artifacts
make requirements-dev   # Generate requirements-dev.txt
```

---

## 🛠️ Technology Choices

### **Pipenv > pip + venv**

**Why Pipenv?**
- ✅ **Deterministic builds** - `Pipfile.lock` ensures same versions everywhere
- ✅ **Separate dev deps** - `--dev` flag for test/lint tools
- ✅ **Automatic venv management** - No manual activation
- ✅ **Security scanning** - Built-in `pipenv check`
- ✅ **Easy requirements.txt generation** - `pipenv requirements > requirements.txt`

**This template uses Pipenv locally, generates `requirements.txt` for Lambda deployment.**

### **AWS Lambda Powertools**

Not using Powertools? You're rebuilding features AWS already built:
- **Structured logging** with correlation IDs
- **Distributed tracing** with X-Ray
- **Custom metrics** to CloudWatch
- **Request validation** with Pydantic
- **Type-safe event handling** for API Gateway

### **Makefile for Cross-Platform Commands**

One command interface for Mac, Linux, and Windows (via Git Bash or WSL):
```bash
make build  # Same command everywhere
```

No more "How do I run this on Windows?" Slack messages.

---

## 🧪 Testing & Quality

### **Comprehensive Test Suite**
- **98%+ code coverage** (enforced in CI)
- **Fixture composition** via `conftest.py`
- **Mock Lambda context** for realistic testing
- **Separate fixtures** for different event types

### **Linting & Code Quality**
```bash
make lint  # Runs all pre-commit hooks
```

Pre-configured with **pre-commit hooks**:
- **black** - Opinionated code formatter
- **isort** - Import statement organizer
- **flake8** - Style guide enforcement
- **autopep8** - PEP 8 auto-formatting
- **pyupgrade** - Automatic Python syntax modernization (3.9+)
- **Pre-commit hooks** - YAML/JSON/TOML validation, trailing whitespace, etc.
- **pytest** - Runs full test suite on commit

**Why?** Consistent code style. Catch issues before CI. No more "fix linting" commits.

---

## 📁 Project Structure

```
.
├── src/
│   ├── app.py              # Routes only (clean!)
│   ├── decorators.py       # @unified_response decorator
│   ├── exceptions.py       # Custom exceptions + handler registration
│   ├── models.py           # Pydantic request/response models
│   └── helper.py           # Business logic & domain models
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── test_handler.py     # Endpoint tests
│   └── fixtures/           # JSON event fixtures
├── template.yaml           # SAM template with CloudWatch alarms
├── Pipfile                 # Dependency management
├── makefile                # Build & test commands
└── env.json.example        # Local environment variables
```

---

## 🎨 Key Features

### **1. Health Check Endpoint**
```python
@app.get("/health")
@unified_response
def health_check() -> dict[str, Any]:
    return {"status": "healthy", ...}
```

Ready for load balancers, monitoring tools, and uptime checks.

### **2. Structured Error Responses**
```python
raise NotFoundError(
    "User not found",
    resource_type="User",
    resource_id="123"
)
```

Returns:
```json
{
  "success": false,
  "data": null,
  "error": {
    "type": "NotFoundError",
    "message": "User not found",
    "details": {"resource_type": "User", "resource_id": "123"}
  }
}
```

### **3. EventBridge Scheduled Events**
Lambda supports both API calls and scheduled execution:
```yaml
Events:
  ApiEvent:
    Type: Api
  NightlySchedule:
    Type: Schedule
    Properties:
      Schedule: "cron(0 0 * * ? *)"
```

### **4. Native AWS Environment Configuration**
No custom config classes - uses standard AWS patterns:
- `env.json` for local development
- Environment variables in `template.yaml`
- AWS Secrets Manager / Parameter Store for production

### **5. CloudWatch Alarms**
Pre-configured alarms for:
- Lambda errors (5+ errors in 5 minutes)
- Lambda throttles (any throttling)

---

## 📚 Documentation

- **`DEVELOPMENT.md`** - Complete setup guide, environment variables, CI/CD, troubleshooting
- **`README.md`** - This file (project overview & architectural highlights)

---

## 🏗️ Production Readiness

### **What's Included**
✅ Structured logging with correlation IDs
✅ Distributed tracing (X-Ray)
✅ Custom metrics to CloudWatch
✅ Error monitoring with alarms
✅ Health check endpoint
✅ Request validation
✅ Type safety throughout
✅ 98%+ test coverage
✅ Scheduled event support
✅ Pre-configured IAM roles

### **What You Need to Add**
- Database connection (DynamoDB, RDS, etc.)
- Authentication/Authorization
- Rate limiting
- CORS configuration (if needed)
- API Gateway custom domain

---

## 🔧 Configuration

### **Local Development**
1. Copy `env.json.example` to `env.json`
2. Update environment variables
3. Run `make start`

### **Deployment**
```bash
# Build
sam build --use-container

# Deploy
sam deploy --guided
```

---

## 🤝 Contributing

This is a **template repository** - fork it and make it your own!

### **Philosophy**
- **Opinionated but flexible** - Strong defaults, easy to customize
- **Production patterns** - Not just "hello world"
- **Educational** - Comments explain WHY, not just WHAT
- **Maintainable** - Code you can hand off at 2am

---

## 📝 License

MIT - Use it however you want!

---

## 🙏 Credits

Built with:
- [AWS SAM CLI](https://aws.amazon.com/serverless/sam/)
- [AWS Lambda Powertools for Python](https://awslabs.github.io/aws-lambda-powertools-python/)
- [Pydantic](https://docs.pydantic.dev/)
- [Pytest](https://pytest.org/)

---

**Questions? Issues? Fork it and make it better!** 🚀
