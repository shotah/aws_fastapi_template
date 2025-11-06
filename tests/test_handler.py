import json
from typing import Any

from src.app import lambda_handler
from tests.conftest import MockLambdaContext


def _modify_event_for_post_users(
    event: dict[str, Any], body_data: dict[str, Any]
) -> dict[str, Any]:
    """Helper to modify event for POST /users endpoint"""
    event["httpMethod"] = "POST"
    event["path"] = "/users"
    event["resource"] = "/users"
    event["requestContext"]["httpMethod"] = "POST"
    event["requestContext"]["path"] = "/users"
    event["requestContext"]["resourcePath"] = "/users"
    event["body"] = json.dumps(body_data)
    event["headers"]["Content-Type"] = "application/json"
    return event


def test_lambda_handler(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test the /hello GET endpoint"""
    # Base event is already configured for GET /hello
    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    # Check ApiResponse envelope
    assert response["success"] is True
    assert response["error"] is None
    assert "data" in response

    # Check actual data payload
    data = response["data"]
    assert data["message"] == "hello world"
    # Test that helper module was called successfully
    assert "helper_module_test" in data
    assert data["helper_module_test"]["greeting"] == "Hello, Lambda!"
    assert data["helper_module_test"]["source"] == "helper module"
    assert data["helper_module_test"]["status"] == "success"
    # Test multiplication result
    assert "multiplication_result" in data
    assert data["multiplication_result"] == 42


def test_create_user_valid(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test the /users POST endpoint with valid data"""
    event = _modify_event_for_post_users(
        base_apigw_event,
        {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "is_active": True,
        },
    )

    ret = lambda_handler(event, lambda_context)
    response = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    # Check ApiResponse envelope
    assert response["success"] is True
    assert response["error"] is None
    assert "data" in response

    # Check actual data payload
    data = response["data"]
    assert data["status"] == "success"
    assert "User John Doe created successfully" in data["message"]
    # User is now a domain model from helper.py with user_id
    assert data["user"]["user_id"] == 1000  # First user from Users service
    assert data["user"]["name"] == "John Doe"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["age"] == 30
    assert data["user"]["is_active"] is True


def test_create_user_invalid_age(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test the /users POST endpoint with invalid age (validation should fail)"""
    event = _modify_event_for_post_users(
        base_apigw_event,
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "age": 200,  # Invalid: exceeds max of 150
        },
    )

    ret = lambda_handler(event, lambda_context)

    # Should return 422 (Unprocessable Entity) due to validation error
    assert ret["statusCode"] == 422


def test_nightly_email_schedule(
    lambda_context: MockLambdaContext, mock_verified_email: str
) -> None:
    """
    Test Lambda handler with midnight scheduled event for nightly emails.

    This is an integration test that verifies:
    - EventBridge schedule triggers the Lambda (using API Gateway event format)
    - Lambda handler routes via app.resolve() to /tasks/nightly-email endpoint
    - EmailService sends the daily report
    - Proper ApiResponse format is returned

    NOTE: EventBridge sends an API Gateway-compatible event (see template.yaml)
    This allows scheduled tasks to use the same exception handling path.
    """
    import os

    # Set up admin email for daily report
    admin_email = "admin@example.com"
    os.environ["ADMIN_EMAIL"] = admin_email
    os.environ["ENVIRONMENT"] = "Test"

    # Create a minimal scheduled event in API Gateway format
    # EventBridge sends this format (see template.yaml NightlySchedule Input)
    # This allows scheduled tasks to use the same exception handling as API endpoints
    scheduled_event = {
        "httpMethod": "POST",
        "path": "/tasks/nightly-email",
        "resource": "/tasks/nightly-email",
        "requestContext": {
            "requestId": "eventbridge-scheduled-task",
        },
        "isBase64Encoded": False,
    }

    ret = lambda_handler(scheduled_event, lambda_context)

    # Should return API Gateway response with ApiResponse body
    assert ret["statusCode"] == 200
    body = json.loads(ret["body"])
    assert body["success"] is True
    assert body["error"] is None
    assert "Email sent successfully" in body["data"]["message"]
    assert "message_id" in body["data"]
    assert body["data"]["recipient"] == admin_email


def test_health_check(base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext) -> None:
    """Test the /health GET endpoint"""
    # Modify event for health check
    base_apigw_event["path"] = "/health"
    base_apigw_event["resource"] = "/health"
    base_apigw_event["requestContext"]["path"] = "/health"
    base_apigw_event["requestContext"]["resourcePath"] = "/health"

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    # Check ApiResponse envelope
    assert response["success"] is True
    assert response["error"] is None
    assert "data" in response

    # Check actual health data
    data = response["data"]
    assert data["status"] == "healthy"
    assert "service" in data
    assert "environment" in data
    assert "checks" in data
    assert data["checks"]["lambda"] == "ok"


def test_get_user_success(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test GET /users/{user_id} with valid user ID"""
    # Modify event for GET /users/1000
    base_apigw_event["path"] = "/users/1000"
    base_apigw_event["resource"] = "/users/{user_id}"
    base_apigw_event["pathParameters"] = {"user_id": "1000"}
    base_apigw_event["requestContext"]["path"] = "/users/1000"
    base_apigw_event["requestContext"]["resourcePath"] = "/users/{user_id}"

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    # Check ApiResponse envelope
    assert response["success"] is True
    assert response["error"] is None
    assert "data" in response

    # Check actual user data
    data = response["data"]
    assert data["user_id"] == 1000
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"


def test_get_user_not_found(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test GET /users/{user_id} with non-existent user ID"""
    # Modify event for GET /users/9999
    base_apigw_event["path"] = "/users/9999"
    base_apigw_event["resource"] = "/users/{user_id}"
    base_apigw_event["pathParameters"] = {"user_id": "9999"}
    base_apigw_event["requestContext"]["path"] = "/users/9999"
    base_apigw_event["requestContext"]["resourcePath"] = "/users/{user_id}"

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    # Should return 404 with NotFoundError
    assert ret["statusCode"] == 404
    # Check ApiResponse envelope for errors
    assert response["success"] is False
    assert response["data"] is None
    assert response["error"] is not None

    # Check error details
    error = response["error"]
    assert error["type"] == "NotFoundError"
    assert "not found" in error["message"]
    assert error["details"]["resource_type"] == "User"
    assert error["details"]["resource_id"] == "9999"


def test_get_user_invalid_id(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test GET /users/{user_id} with invalid user ID format"""
    # Modify event for GET /users/abc
    base_apigw_event["path"] = "/users/abc"
    base_apigw_event["resource"] = "/users/{user_id}"
    base_apigw_event["pathParameters"] = {"user_id": "abc"}
    base_apigw_event["requestContext"]["path"] = "/users/abc"
    base_apigw_event["requestContext"]["resourcePath"] = "/users/{user_id}"

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    # Should return 400 with ValidationError
    assert ret["statusCode"] == 400
    # Check ApiResponse envelope for errors
    assert response["success"] is False
    assert response["data"] is None
    assert response["error"] is not None

    # Check error details
    error = response["error"]
    assert error["type"] == "ValidationError"
    assert "Invalid user ID format" in error["message"]
    assert error["details"]["user_id"] == "abc"


def test_create_user_type_error(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test POST /users with wrong type for age field (string instead of int)

    NOTE: Pydantic type validation errors are handled by Powertools internally
    and return in Powertools' standard format (not our ApiResponse wrapper).
    This is by design - Powertools catches type/format errors before our handlers.

    Our custom business logic validation (like age > 150) DOES go through our
    exception handler and returns in ApiResponse format.
    """
    # Modify event for POST /users with invalid type
    base_apigw_event["httpMethod"] = "POST"
    base_apigw_event["path"] = "/users"
    base_apigw_event["resource"] = "/users"
    base_apigw_event["requestContext"]["httpMethod"] = "POST"
    base_apigw_event["requestContext"]["path"] = "/users"
    base_apigw_event["requestContext"]["resourcePath"] = "/users"
    # Send string "onehundred" instead of integer 100
    base_apigw_event["body"] = json.dumps(
        {"name": "Jane Doe", "email": "jane@example.com", "age": "onehundred"}
    )

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    # Should return 422 (Unprocessable Entity) for Pydantic validation error
    assert ret["statusCode"] == 422

    # Powertools returns validation errors in its own format
    # (not our ApiResponse wrapper)
    # Format: {"statusCode": 422, "detail": [{"loc": ["body", "age"], ...}]}
    assert "statusCode" in response or "detail" in response or "message" in response

    # Verify the error mentions the age field
    response_str = json.dumps(response).lower()
    assert "age" in response_str


def test_create_user_missing_required_field(
    base_apigw_event: dict[str, Any], lambda_context: MockLambdaContext
) -> None:
    """Test POST /users with missing required field (email)

    In Pydantic, fields with Field(...) are REQUIRED (the ... means no default).
    Optional fields have default values like Field(default=True).

    Missing required fields are caught by Powertools validation (422 error).
    """
    # Modify event for POST /users
    base_apigw_event["httpMethod"] = "POST"
    base_apigw_event["path"] = "/users"
    base_apigw_event["resource"] = "/users"
    base_apigw_event["requestContext"]["httpMethod"] = "POST"
    base_apigw_event["requestContext"]["path"] = "/users"
    base_apigw_event["requestContext"]["resourcePath"] = "/users"
    # Missing required field: email (name, email, age are all required)
    base_apigw_event["body"] = json.dumps({"name": "Jane Doe", "age": 30})

    ret = lambda_handler(base_apigw_event, lambda_context)
    response = json.loads(ret["body"])

    # Should return 422 (Unprocessable Entity) for missing required field
    assert ret["statusCode"] == 422

    # Powertools returns validation errors for missing required fields
    assert "statusCode" in response or "detail" in response or "message" in response

    # Verify the error mentions the email field
    response_str = json.dumps(response).lower()
    assert "email" in response_str
