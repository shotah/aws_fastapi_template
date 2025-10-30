"""Request and Response models for API endpoints.

This module contains ONLY API contracts (requests and responses).
Domain models (like User) are imported from helper.py where business logic lives.
"""

from pydantic import BaseModel, ConfigDict, Field

# Import domain models from helper.py - no circular dependency!
# helper.py uses TYPE_CHECKING for imports from models.py, so this is safe
from helper import User

# ============================================================================
# Request Models
# ============================================================================


class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "is_active": True,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: str = Field(..., description="User's email address")
    age: int = Field(..., ge=0, le=150, description="User's age")
    is_active: bool = Field(default=True, description="Whether the user is active")


# ============================================================================
# Response Models
# ============================================================================


class HelperModuleTest(BaseModel):
    """Helper module test result."""

    greeting: str
    source: str
    status: str


class HelloResponse(BaseModel):
    """Response model for GET /hello endpoint."""

    message: str
    helper_module_test: HelperModuleTest
    multiplication_result: int


class UserCreateResponse(BaseModel):
    """
    Response model for POST /users endpoint.

    Uses the User domain model from helper.py - avoiding duplication!
    The User class represents business logic, not an API contract,
    so it lives in helper.py.
    """

    status: str
    message: str
    user: User  # Using domain model directly - no duplication!
