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
from models import (
    FileListResponse,
    FileUploadRequest,
    FileUploadResponse,
    HelloResponse,
    UserCreateResponse,
    UserResponse,
)
from services.email import EmailService  # type: ignore
from services.storage import StorageService  # type: ignore

# ============================================================================
# Eager initialization of boto3 clients (cold start optimization)
# ============================================================================
# boto3 clients are created once at module load (cold start) and cached.
# This moves ~50-100ms of client creation from first request to cold start.
# The singleton pattern in each service ensures these same instances are reused.
#
# Trade-off: If a service isn't used in every invocation, you pay the cost anyway.
# For most Lambda use cases, this is worth it for faster first-request latency.
#
# Conditional init: Only if env vars are set (allows tests to import without error)
if os.getenv("DATA_BUCKET"):
    _storage_service = StorageService()
if os.getenv("FROM_EMAIL"):
    _email_service = EmailService()

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


# ============================================================================
# Storage Endpoints (S3 Integration Example)
# ============================================================================


@app.post("/files")
@unified_response
@tracer.capture_method
def upload_file(upload_request: FileUploadRequest) -> dict[str, Any]:
    """
    Upload a file to S3.

    Demonstrates:
    - S3 integration via StorageService
    - Base64 decoding
    - File size calculation
    - Error handling for storage operations

    Request body:
        {
            "file_name": "document.pdf",
            "content": "base64_encoded_content",
            "content_type": "application/pdf",
            "metadata": {"author": "John Doe"}
        }

    Returns:
        File upload response with S3 key and size
    """
    import base64

    metrics.add_metric(name="FileUploads", unit=MetricUnit.Count, value=1)

    try:
        # Decode base64 content
        file_content = base64.b64decode(upload_request.content)

        # Generate S3 key (you might want to use UUID or timestamp)
        import uuid

        file_id = f"uploads/{uuid.uuid4()}/{upload_request.file_name}"

        # Upload to S3
        storage = StorageService()
        storage.upload_file(
            file_content=file_content,
            key=file_id,
            content_type=upload_request.content_type,
            metadata=upload_request.metadata or {},
        )

        logger.info(f"File uploaded successfully: {file_id}", extra={"size": len(file_content)})

        return FileUploadResponse(
            file_id=file_id,
            file_name=upload_request.file_name,
            size=len(file_content),
            message="File uploaded successfully",
        ).model_dump()

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        metrics.add_metric(name="FileUploadErrors", unit=MetricUnit.Count, value=1)
        raise ValidationError(f"Failed to upload file: {str(e)}")


@app.get("/files/<file_id>")
@unified_response
@tracer.capture_method
def download_file(file_id: str) -> dict[str, Any]:
    """
    Download a file from S3.

    Path parameter:
        file_id: S3 key (e.g., "uploads/uuid/filename.pdf")

    Returns:
        File content as base64-encoded string with metadata
    """
    import base64

    metrics.add_metric(name="FileDownloads", unit=MetricUnit.Count, value=1)

    try:
        storage = StorageService()

        # Check if file exists
        if not storage.file_exists(file_id):
            raise NotFoundError(f"File not found: {file_id}")

        # Download file
        file_content = storage.download_file(file_id)

        logger.info(f"File downloaded successfully: {file_id}", extra={"size": len(file_content)})

        return {
            "file_id": file_id,
            "content": base64.b64encode(file_content).decode("utf-8"),
            "size": len(file_content),
            "message": "File downloaded successfully",
        }

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        metrics.add_metric(name="FileDownloadErrors", unit=MetricUnit.Count, value=1)
        raise ValidationError(f"Failed to download file: {str(e)}")


@app.get("/files")
@unified_response
@tracer.capture_method
def list_files() -> dict[str, Any]:
    """
    List all files in S3 bucket.

    Query parameters:
        prefix (optional): Filter files by prefix (e.g., "uploads/")

    Returns:
        List of files with metadata (key, size, last_modified)
    """
    metrics.add_metric(name="FileListRequests", unit=MetricUnit.Count, value=1)

    try:
        # Get optional prefix from query parameters
        prefix = app.current_event.get_query_string_value("prefix", default_value="")

        storage = StorageService()
        files = storage.list_files(prefix=prefix)

        logger.info(f"Listed {len(files)} files", extra={"prefix": prefix})

        return FileListResponse(files=files, count=len(files)).model_dump()

    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        metrics.add_metric(name="FileListErrors", unit=MetricUnit.Count, value=1)
        raise ValidationError(f"Failed to list files: {str(e)}")


@app.delete("/files/<file_id>")
@unified_response
@tracer.capture_method
def delete_file(file_id: str) -> dict[str, Any]:
    """
    Delete a file from S3.

    Path parameter:
        file_id: S3 key (e.g., "uploads/uuid/filename.pdf")

    Returns:
        Success message
    """
    metrics.add_metric(name="FileDeletions", unit=MetricUnit.Count, value=1)

    try:
        storage = StorageService()

        # Check if file exists
        if not storage.file_exists(file_id):
            raise NotFoundError(f"File not found: {file_id}")

        # Delete file
        storage.delete_file(file_id)

        logger.info(f"File deleted successfully: {file_id}")

        return {"file_id": file_id, "message": "File deleted successfully"}
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        metrics.add_metric(name="FileDeletionErrors", unit=MetricUnit.Count, value=1)
        raise ValidationError(f"Failed to delete file: {str(e)}")


# ============================================================================
# Scheduled Task Endpoints
# ============================================================================
# NOTE: These endpoints are triggered by EventBridge on a schedule, but they're
# implemented as regular API endpoints. This allows them to:
# 1. Use the same exception handling as API endpoints (register_exception_handlers)
# 2. Be tested/triggered manually via API Gateway if needed
# 3. Maintain consistent response format (ApiResponse)
#
# EventBridge sends an API Gateway-compatible event (see template.yaml NightlySchedule)


@app.post("/tasks/nightly-email")
@unified_response
@tracer.capture_method
def trigger_nightly_email() -> dict[str, Any]:
    """
    Send scheduled nightly emails via SES.

    This endpoint is triggered by EventBridge at midnight (see template.yaml).
    Can also be called manually via API Gateway for testing.

    Returns:
        Dict with success message (automatically wrapped in ApiResponse by decorator)

    Raises:
        ValidationError: If email sending fails (caught by register_exception_handlers)
    """
    metrics.add_metric(name="ScheduledEmailsSent", unit=MetricUnit.Count, value=1)

    # Get admin email from environment
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    # Get email service and send daily report
    email_service = EmailService()

    # Optional: Customize report content here
    # custom_content = "<h2>Custom Report</h2><p>Your data here</p>"
    # message_id = email_service.send_daily_report(
    #     [admin_email], report_content=custom_content
    # )

    # Send default daily report - exceptions caught by register_exception_handlers
    message_id = email_service.send_daily_report(to_addresses=[admin_email])

    metrics.add_metric(name="EmailsSentSuccess", unit=MetricUnit.Count, value=1)
    logger.info(
        "Nightly email sent successfully",
        extra={"message_id": message_id, "recipient": admin_email},
    )

    return {
        "message": f"Email sent successfully. MessageId: {message_id}",
        "message_id": message_id,
        "recipient": admin_email,
    }


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """
    Main Lambda handler for API Gateway events.

    All events (HTTP requests and EventBridge scheduled tasks) go through app.resolve().
    This provides unified exception handling via register_exception_handlers(app).

    Event Sources:
    - API Gateway: Real HTTP requests from users
    - EventBridge: Scheduled tasks formatted as API Gateway events (see template.yaml)

    Exception Handling:
    - All exceptions caught by register_exception_handlers(app)
    - Returns consistent ApiResponse format for both event types
    """
    return app.resolve(event, context)
