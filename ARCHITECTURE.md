# Architecture Guidelines

## Project Structure & Organization

This document outlines the recommended structure for organizing models, routes, and business logic as the project grows.

---

## Model Organization Strategy

### Guiding Principle: **YAGNI (You Aren't Gonna Need It)**

Start simple and evolve structure only when complexity demands it. Don't create abstractions before they're needed.

---

## Current Size (2-5 endpoints) ✅ **YOU ARE HERE**

### Structure
```
src/
├── app.py          # Routes/handlers
├── models.py       # All models (requests + responses)
└── helper.py       # Utility functions
```

### Why This Works
- **Simple**: Everything is easy to find
- **Fast**: No time wasted navigating complex directories
- **Maintainable**: Minimal cognitive overhead

### When to Evolve
When you have **6+ endpoints** or **20+ models**, consider moving to the next level.

---

## Medium Size (6-15 endpoints)

### Structure: Group by Domain/Feature

```
src/
├── app.py                    # Main app, registers routes
├── users/
│   ├── __init__.py
│   ├── models.py            # User-related models (requests + responses)
│   └── routes.py            # User route handlers
├── auth/
│   ├── __init__.py
│   ├── models.py            # Auth models
│   └── routes.py            # Auth handlers
├── products/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
└── shared/
    ├── __init__.py
    └── models.py            # Shared models (errors, pagination, etc.)
```

### Migration Example

**Before (single file):**
```python
# src/models.py
class UserCreateRequest(BaseModel):
    ...

class ProductCreateRequest(BaseModel):
    ...

# src/app.py
@app.post("/users")
def create_user(user: UserCreateRequest):
    ...

@app.post("/products")
def create_product(product: ProductCreateRequest):
    ...
```

**After (domain-based):**
```python
# src/users/models.py
class UserCreateRequest(BaseModel):
    ...

# src/users/routes.py
from users.models import UserCreateRequest, UserCreateResponse

def create_user(user: UserCreateRequest) -> dict[str, Any]:
    ...

# src/products/models.py
class ProductCreateRequest(BaseModel):
    ...

# src/products/routes.py
from products.models import ProductCreateRequest, ProductCreateResponse

def create_product(product: ProductCreateRequest) -> dict[str, Any]:
    ...

# src/app.py
from users.routes import create_user
from products.routes import create_product

app.post("/users")(create_user)
app.post("/products")(create_product)
```

---

## Large Size (15+ endpoints)

### Structure: Full Feature Modules with Layers

```
src/
├── app.py                    # Main application entry point
├── users/
│   ├── __init__.py
│   ├── models.py            # Pydantic models (request/response)
│   ├── routes.py            # Route handlers (thin)
│   ├── service.py           # Business logic
│   └── repository.py        # Data access layer
├── products/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── service.py
│   └── repository.py
├── orders/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── service.py
│   └── repository.py
└── shared/
    ├── __init__.py
    ├── models.py            # Common response models
    ├── exceptions.py        # Custom exceptions
    ├── dependencies.py      # Dependency injection
    └── middleware.py        # Custom middleware
```

### Layer Responsibilities

#### **models.py** - Data Transfer Objects
```python
from pydantic import BaseModel, Field

class UserCreateRequest(BaseModel):
    """Request validation"""
    name: str = Field(..., min_length=1)
    email: str

class UserResponse(BaseModel):
    """Response schema"""
    id: int
    name: str
    email: str
```

#### **routes.py** - HTTP Layer (Thin)
```python
from typing import Any
from users.models import UserCreateRequest, UserResponse
from users.service import UserService

def create_user(user: UserCreateRequest) -> dict[str, Any]:
    """Route handler - delegates to service layer"""
    service = UserService()
    result = service.create_user(user)
    return UserResponse(**result).model_dump()
```

#### **service.py** - Business Logic
```python
from users.models import UserCreateRequest
from users.repository import UserRepository

class UserService:
    """Business logic layer"""

    def __init__(self):
        self.repo = UserRepository()

    def create_user(self, request: UserCreateRequest) -> dict:
        # Validation, business rules, orchestration
        if self.repo.email_exists(request.email):
            raise ValueError("Email already exists")

        return self.repo.create(request.model_dump())
```

#### **repository.py** - Data Access
```python
class UserRepository:
    """Data access layer"""

    def create(self, user_data: dict) -> dict:
        # Database operations
        ...

    def email_exists(self, email: str) -> bool:
        # Check if email exists
        ...
```

---

## Decision Matrix

| Project Size | Endpoints | Models | Structure | Layers |
|--------------|-----------|--------|-----------|--------|
| **Small** | 2-5 | < 20 | Single `models.py` | Routes only |
| **Medium** | 6-15 | 20-50 | Domain modules | Routes + Models |
| **Large** | 15+ | 50+ | Feature modules | Routes + Service + Repository |

---

## Shared Models

As your project grows, you'll have models used across multiple domains:

### Common Response Models

```python
# src/shared/models.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: list[T]
    total: int
    page: int
    page_size: int

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: dict | None = None

class SuccessResponse(BaseModel):
    """Generic success response"""
    status: str = "success"
    message: str
```

### Usage

```python
# src/users/routes.py
from shared.models import PaginatedResponse
from users.models import UserResponse

def list_users() -> dict[str, Any]:
    users = user_service.get_all()
    response = PaginatedResponse[UserResponse](
        items=[UserResponse(**u) for u in users],
        total=len(users),
        page=1,
        page_size=10
    )
    return response.model_dump()
```

---

## Anti-Patterns to Avoid

### ❌ Don't: Organize by Type
```
src/
├── requests/      # All request models
├── responses/     # All response models
└── handlers/      # All route handlers
```
**Why:** Hard to understand feature boundaries. Changes require touching multiple directories.

### ❌ Don't: One File Per Model
```
src/models/
├── user_create_request.py
├── user_create_response.py
├── user_update_request.py
└── user_update_response.py
```
**Why:** Too granular. Related models should live together.

### ❌ Don't: Premature Abstraction
```
src/
├── core/
│   ├── abstract_service.py
│   ├── base_repository.py
│   └── generic_handler.py
```
**Why:** You have 3 endpoints. Don't build frameworks before you need them.

---

## Migration Checklist

### When Moving from Small → Medium

- [ ] Group endpoints by domain (users, products, orders, etc.)
- [ ] Create `domain/models.py` for each domain
- [ ] Create `domain/routes.py` for route handlers
- [ ] Move related models together
- [ ] Update imports in `app.py`
- [ ] Run tests to verify nothing broke
- [ ] Update documentation

### When Moving from Medium → Large

- [ ] Identify complex business logic in routes
- [ ] Extract business logic to `service.py`
- [ ] Create `repository.py` for data access
- [ ] Identify shared models → move to `shared/`
- [ ] Add custom exceptions if needed
- [ ] Consider dependency injection
- [ ] Run tests to verify nothing broke
- [ ] Update documentation

---

## Key Principles

1. **Start Simple** - Don't over-engineer early
2. **Evolve Gradually** - Refactor when complexity demands it
3. **Domain-Driven** - Group by feature/domain, not by technical layer
4. **Clear Boundaries** - Each layer has a single responsibility
5. **Test Coverage** - Maintain tests during refactoring
6. **YAGNI** - Build what you need now, not what you might need

---

## Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [AWS Lambda Powertools](https://awslabs.github.io/aws-lambda-powertools-python/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)

---

*Last Updated: October 30, 2025*
