import os
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from decorators import unified_response  # type: ignore
from exceptions import NotFoundError, ValidationError, register_exception_handlers  # type: ignore
from helper import Users, get_greeting_message, multiply_numbers  # type: ignore
from models import UserCreateRequest  # type: ignore
from models import HelloResponse, UserCreateResponse, UserResponse

app = APIGatewayRestResolver(enable_validation=True)
tracer = Tracer()
logger = Logger()
metrics = Metrics(namespace=os.getenv("POWERTOOLS_METRICS_NAMESPACE", "Powertools"))

# Register exception handlers (defined in exceptions.py)
register_exception_handlers(app)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
@unified_response
def health_check() -> dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.

    Returns service status, version, and configuration information.
    This endpoint does NOT require authentication and should be fast.

    Returns:
        dict: Health data (automatically wrapped in ApiResponse)
    """
    metrics.add_metric(name="HealthChecks", unit=MetricUnit.Count, value=1)

    return {
        "status": "healthy",
        "service": os.getenv("POWERTOOLS_SERVICE_NAME", "PowertoolsHelloWorld"),
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "checks": {
            "lambda": "ok",
            # Add more checks as needed:
            # "database": check_database(),
            # "cache": check_cache(),
            # "external_api": check_external_api(),
        },
    }


@app.post("/users")
@unified_response
@tracer.capture_method
def create_user(user_request: UserCreateRequest) -> dict[str, Any]:
    """
    Create a new user with Pydantic validation and business logic.

    Flow:
    1. user_request is automatically validated by Pydantic (API contract)
    2. Users service handles business logic
    3. Returns domain User model
    4. Wrapped in UserCreateResponse (API contract)
    5. Automatically wrapped in ApiResponse envelope by decorator

    This demonstrates proper separation:
    - API models (UserCreateRequest/Response) in models.py
    - Domain model (User) in helper.py
    - Business logic (Users service) in helper.py
    - Orchestration here in app.py
    """
    metrics.add_metric(name="UserCreationAttempts", unit=MetricUnit.Count, value=1)

    logger.info("Creating new user", extra={"user_email": user_request.email})

    # Business logic in Users service - returns domain User model
    users_service = Users()
    user = users_service.create_user(
        name=user_request.name,
        email=user_request.email,
        age=user_request.age,
        is_active=user_request.is_active,
    )

    # Return UserCreateResponse - decorator will wrap in ApiResponse
    return UserCreateResponse(
        status="success",
        message=f"User {user_request.name} created successfully",
        user=user,  # Domain model from helper.py!
    ).model_dump()


@app.get("/users/<user_id>")
@unified_response
@tracer.capture_method
def get_user(user_id: str) -> dict[str, Any]:
    """
    Get a user by ID (demonstrates error handling).

    Args:
        user_id: User ID from path parameter

    Returns:
        dict: User data (automatically wrapped in ApiResponse)

    Raises:
        NotFoundError: If user is not found
        ValidationError: If user_id is invalid
    """
    metrics.add_metric(name="GetUserRequests", unit=MetricUnit.Count, value=1)

    # Validate user_id format
    if not user_id.isdigit():
        raise ValidationError(
            "Invalid user ID format", details={"user_id": user_id, "expected": "numeric string"}
        )

    # Convert to int
    user_id_int = int(user_id)

    # Simulate database lookup
    # In a real app, this would query DynamoDB or another database
    logger.info(f"Looking up user {user_id_int}")

    # Demo: Only return user if ID is 1000 (first user from Users service)
    if user_id_int == 1000:
        return UserResponse(
            user_id=1000, name="John Doe", email="john@example.com", age=30, is_active=True
        ).model_dump()

    # User not found - raise custom exception
    raise NotFoundError(
        f"User with ID {user_id} not found", resource_type="User", resource_id=user_id
    )


@app.get("/hello")
@unified_response
@tracer.capture_method
def hello() -> dict[str, Any]:
    """
    Example endpoint using helper function that returns Pydantic model.

    Demonstrates the circular dependency solution:
    - get_greeting_message() returns HelperModuleTest
    - Uses TYPE_CHECKING and runtime import in helper.py
    - No circular dependency issues!
    - Response automatically wrapped in ApiResponse by decorator
    """
    # adding custom metrics
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/metrics/
    metrics.add_metric(name="HelloWorldInvocations", unit=MetricUnit.Count, value=1)

    # Helper function returns a Pydantic model directly - no circular import!
    greeting_model = get_greeting_message("Lambda")
    test_multiply = multiply_numbers(6, 7)

    # structured log
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/logger/
    logger.info("Hello world API - HTTP 200", extra={"helper_greeting": greeting_model.greeting})

    # Return data - decorator will wrap in ApiResponse
    return HelloResponse(
        message="hello world",
        helper_module_test=greeting_model,  # Already a Pydantic model!
        multiplication_result=test_multiply,
    ).model_dump()


def handle_scheduled_event(event: dict) -> dict[str, Any]:
    """
    Handle EventBridge scheduled events (e.g., nightly processing).

    This function is called when the Lambda is triggered by a schedule,
    not through API Gateway.
    """
    logger.info("Scheduled event triggered", extra={"event": event})
    metrics.add_metric(name="ScheduledExecutions", unit=MetricUnit.Count, value=1)

    # Extract custom input from the schedule event
    event_source = event.get("source", "unknown")
    detail = event.get("detail", {})

    # Your nightly processing logic here
    logger.info("Running nightly processing", extra={"source": event_source, "detail": detail})

    # Example: Add your business logic here
    # users_service = Users()
    # users_service.run_nightly_cleanup()
    # users_service.generate_reports()

    return {"statusCode": 200, "body": "Scheduled processing completed successfully"}


# Enrich logging with contextual information from Lambda
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
# Adding tracer
# See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/tracer/
@tracer.capture_lambda_handler
# ensures metrics are flushed upon request completion/failure and
# capturing ColdStart metric
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """
    Main Lambda handler that routes to appropriate handler based on event source.

    Supports:
    - API Gateway events (HTTP requests)
    - EventBridge Schedule events (cron/rate)
    """
    # Check if this is a scheduled event from EventBridge
    if event.get("source") == "aws.events" and event.get("detail-type") == "Scheduled Event":
        logger.info("Detected EventBridge scheduled event")
        return handle_scheduled_event(event)

    # Otherwise, treat as API Gateway event
    return app.resolve(event, context)
