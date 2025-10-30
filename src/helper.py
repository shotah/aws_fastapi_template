"""Helper module with domain models, utility functions, and services.

This module demonstrates:
1. Domain models (User) that represent business entities
2. Service classes (Users) that contain business logic
3. How to handle circular dependencies when returning API response models

Domain models belong here because they represent business logic, not API contracts.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

# TYPE_CHECKING is False at runtime, True during type checking
# This prevents circular imports while maintaining type safety
if TYPE_CHECKING:
    from models import HelperModuleTest  # type: ignore


# ============================================================================
# Domain Models (Business Objects)
# ============================================================================


class User(BaseModel):
    """
    Domain model representing a User entity.

    This is a business/domain object, NOT an API request/response model.
    It lives in helper.py (or ideally domain.py) because it represents
    core business logic and data structures.
    """

    user_id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: str = Field(..., description="User's email address")
    age: int = Field(..., ge=0, le=150, description="User's age")
    is_active: bool = Field(default=True, description="Whether the user is active")


# ============================================================================
# Service Classes (Business Logic)
# ============================================================================


class Users:
    """
    Service class for managing User collections.

    Contains business logic for user operations.
    This is where you'd add methods for database operations,
    validation, filtering, etc.
    """

    def __init__(self) -> None:
        """Initialize the Users service."""
        self._next_id = 1000

    def create_user(
        self,
        name: str,
        email: str,
        age: int,
        is_active: bool = True,
    ) -> User:
        """
        Create a new user (business logic).

        This is where you'd normally:
        - Validate business rules
        - Save to database
        - Send notifications
        - etc.

        Args:
            name: User's full name
            email: User's email address
            age: User's age
            is_active: Whether the user is active

        Returns:
            A User domain model instance
        """
        user_id = self._next_id
        self._next_id += 1

        return User(
            user_id=user_id,
            name=name,
            email=email,
            age=age,
            is_active=is_active,
        )


# ============================================================================
# Utility Functions
# ============================================================================


def get_greeting_message(name: str = "world") -> "HelperModuleTest":
    """
    Generate a greeting message as a Pydantic model.

    This demonstrates how to handle functions that return Pydantic models
    without creating circular dependencies.

    Args:
        name: The name to greet (default: "world")

    Returns:
        A HelperModuleTest Pydantic model
        (uses forward reference to avoid circular import at module level)
    """
    # Import at runtime inside the function to avoid circular dependency
    from models import HelperModuleTest

    return HelperModuleTest(
        greeting=f"Hello, {name}!",
        source="helper module",
        status="success",
    )


def multiply_numbers(a: int, b: int) -> int:
    """
    Simple function to test module imports.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
