"""Custom exceptions for structured error responses.

Usage:
    raise NotFoundError("User not found", resource_type="User", resource_id="123")
    raise ValidationError("Invalid input", details={"field": "email"})

Add more as needed:
    class ConflictError(AppException):
        def __init__(self, message: str, details: dict | None = None):
            super().__init__(message, status_code=409, details=details)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aws_lambda_powertools.event_handler import APIGatewayRestResolver


# ============================================================================
# Exception Classes
# ============================================================================


class AppException(Exception):
    """Base exception for all application errors with structured details."""

    def __init__(self, message: str, status_code: int = 500, details: dict | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Invalid input (400)."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, status_code=400, details=details)


class NotFoundError(AppException):
    """Resource not found (404)."""

    def __init__(
        self, message: str, resource_type: str | None = None, resource_id: str | None = None
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, status_code=404, details=details)


# ============================================================================
# Exception Handler Registration
# ============================================================================


def register_exception_handlers(app: "APIGatewayRestResolver") -> None:
    """
    Register all exception handlers for the API Gateway resolver.

    This keeps app.py clean by centralizing exception handling logic here.

    Args:
        app: The APIGatewayRestResolver instance to register handlers on

    Usage:
        from exceptions import register_exception_handlers
        app = APIGatewayRestResolver()
        register_exception_handlers(app)
    """
    # Import at runtime to avoid circular dependency
    from aws_lambda_powertools.event_handler import Response

    from models import ApiResponse  # type: ignore

    @app.exception_handler(AppException)
    def handle_app_exception(ex: AppException) -> Response:
        """Convert custom exceptions to consistent ApiResponse envelope."""
        response = ApiResponse(
            success=False,
            data=None,
            error={"type": ex.__class__.__name__, "message": ex.message, "details": ex.details},
        )
        return Response(
            status_code=ex.status_code, content_type="application/json", body=response.model_dump()
        )

    # NOTE: Pydantic type validation errors (e.g., string instead of int) are handled by
    # Powertools internally when enable_validation=True. They return 422 in Powertools' format:
    # {"statusCode": 422, "detail": [{" loc": ["body", "field"], "msg": "...", "type": "..."}]}
    #
    # Our custom business logic validation errors (raised via ValidationError, NotFoundError, etc.)
    # go through handle_app_exception above and return in our ApiResponse
    # envelope format.
