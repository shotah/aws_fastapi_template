"""Request and Response models for API endpoints.

This module contains ONLY API contracts (requests and responses).
Domain models (like User) are imported from helper.py where business logic lives.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Import domain models from helper.py - no circular dependency!
# helper.py uses TYPE_CHECKING for imports from models.py, so this is safe
from helper import User  # type: ignore

# ============================================================================
# Generic API Response Envelope
# ============================================================================

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope for consistent responses.

    Every endpoint returns this structure:
    {
        "success": true,
        "data": { ... },
        "error": null
    }

    Usage:
        return ApiResponse(success=True, data=user_data).model_dump()
        return ApiResponse(success=False, error="Not found").model_dump()
    """

    success: bool = Field(..., description="Whether the request was successful")
    data: T | None = Field(default=None, description="Response data")
    error: str | dict[str, Any] | None = Field(default=None, description="Error message if failed")


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
    is_test: bool = Field(default=True, description="test")
    is_fake: bool = Field(default=False, description="test")


class FileUploadRequest(BaseModel):
    """Request model for uploading a file."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "document.pdf",
                "content": "base64_encoded_content_here",
                "content_type": "application/pdf",
                "metadata": {"author": "John Doe", "version": "1.0"},
            }
        }
    )

    file_name: str = Field(..., min_length=1, max_length=255, description="Name of the file")
    content: str = Field(..., description="Base64-encoded file content")
    content_type: str = Field(default="application/octet-stream", description="MIME type")
    metadata: dict[str, str] | None = Field(default=None, description="Optional metadata")


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


class UserResponse(BaseModel):
    """
    Response model for GET /users/{id} endpoint.

    Uses the User domain model from helper.py directly.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    age: int
    is_active: bool


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


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    file_id: str = Field(..., description="S3 key of the uploaded file")
    file_name: str = Field(..., description="Name of the uploaded file")
    size: int = Field(..., description="Size in bytes")
    message: str = Field(..., description="Success message")


class FileMetadata(BaseModel):
    """Metadata for a file in S3."""

    key: str = Field(..., description="S3 object key")
    size: str = Field(..., description="File size in bytes")
    last_modified: str = Field(..., description="Last modified timestamp")


class FileListResponse(BaseModel):
    """Response model for listing files."""

    files: list[FileMetadata] = Field(..., description="List of files")
    count: int = Field(..., description="Number of files")
