"""Request and Response models for API endpoints."""

from pydantic import BaseModel, ConfigDict, Field

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


class UserData(BaseModel):
    """User data in response."""

    name: str
    email: str
    age: int
    is_active: bool


class UserCreateResponse(BaseModel):
    """Response model for POST /users endpoint."""

    status: str
    message: str
    user: UserData
    generated_id: int
