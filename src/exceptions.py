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


class ScheduledTaskError(AppException):
    """Scheduled task failure (500)."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


# ============================================================================
# Exception Handler Registration & Formatting
# ============================================================================


def format_exception_response(ex: AppException) -> dict:
    """
    Format an AppException into ApiResponse format.

    This is the single source of truth for exception formatting,
    used by both API Gateway handlers and scheduled event handlers.

    Args:
        ex: The AppException to format

    Returns:
        dict: ApiResponse formatted error
    """
    from models import ApiResponse  # type: ignore

    return ApiResponse(
        success=False,
        data=None,
        error={"type": ex.__class__.__name__, "message": ex.message, "details": ex.details},
    ).model_dump()


def register_exception_handlers(app: "APIGatewayRestResolver") -> None:
    """
    Register all exception handlers for the API Gateway resolver.

    This keeps app.py clean by centralizing exception handling logic here.

    Handlers are checked in order:
    1. AppException subclasses (ValidationError, NotFoundError, etc.) - formatted responses
    2. Generic Exception - wrapped in 500 error

    Args:
        app: The APIGatewayRestResolver instance to register handlers on

    Usage:
        from exceptions import register_exception_handlers
        app = APIGatewayRestResolver()
        register_exception_handlers(app)
    """
    # Import at runtime to avoid circular dependency
    from aws_lambda_powertools.event_handler import Response

    @app.exception_handler(AppException)
    def handle_app_exception(ex: AppException) -> Response:
        """
        Convert custom AppException subclasses to consistent ApiResponse envelope.

        Handles: ValidationError, NotFoundError, ScheduledTaskError, etc.
        """
        response_body = format_exception_response(ex)
        return Response(
            status_code=ex.status_code, content_type="application/json", body=response_body
        )

    # NOTE: We DON'T register a catch-all Exception handler because:
    # 1. Powertools handles its own RequestValidationError (Pydantic validation) -> returns 422
    # 2. Other unexpected exceptions should fail loudly in development
    # 3. In production, Lambda catches unhandled exceptions and logs them to CloudWatch
    #
    # Exception Handling Summary:
    # - AppException subclasses (ValidationError, NotFoundError) -> ApiResponse format (above)
    # - RequestValidationError (Pydantic/schema errors) -> Powertools format (422)
    # - Other exceptions -> Let Lambda/CloudWatch handle (500)
