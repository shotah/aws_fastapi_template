"""Decorators for API endpoints.

This module contains reusable decorators for wrapping endpoint responses,
handling authentication, rate limiting, etc.
"""

from functools import wraps
from typing import Any, Callable

from models import ApiResponse  # type: ignore


def unified_response(func: Callable) -> Callable:
    """
    Decorator to automatically wrap endpoint responses in consistent ApiResponse envelope.

    Every successful endpoint response is wrapped as:
    {
        "success": true,
        "data": <endpoint_return_value>,
        "error": null
    }

    Errors are handled by the exception handler, not this decorator.

    Usage:
        @app.get("/endpoint")
        @unified_response
        def my_endpoint():
            return {"key": "value"}  # Automatically wrapped!

    Returns:
        Wrapped function that returns ApiResponse envelope
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = func(*args, **kwargs)
        return ApiResponse(success=True, data=result).model_dump()

    return wrapper
