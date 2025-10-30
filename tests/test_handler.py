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
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
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
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
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
