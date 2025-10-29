import json
from pathlib import Path

import pytest

from src.app import lambda_handler


def lambda_context():
    class LambdaContext:
        def __init__(self):
            self.function_name = "test-func"
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = "arn:aws:lambda:eu-west-1:809313241234:function:test-func"
            self.aws_request_id = "52fdfc07-2182-154f-163f-5f0f9a621d72"

        def get_remaining_time_in_millis(self) -> int:
            return 1000

    return LambdaContext()


@pytest.fixture()
def apigw_event():
    """Loads API Gateway event from JSON fixture file"""
    fixture_path = Path(__file__).parent / "fixtures" / "apigw_hello_event.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_lambda_handler(apigw_event):
    """Test the /hello GET endpoint"""
    ret = lambda_handler(apigw_event, lambda_context())
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


@pytest.fixture()
def apigw_post_event():
    """Loads API Gateway POST event from JSON fixture file"""
    fixture_path = Path(__file__).parent / "fixtures" / "apigw_post_user_event.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_create_user_valid(apigw_post_event):
    """Test the /users POST endpoint with valid data"""
    ret = lambda_handler(apigw_post_event, lambda_context())
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert data["status"] == "success"
    assert "User John Doe created successfully" in data["message"]
    assert data["user"]["name"] == "John Doe"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["age"] == 30
    assert data["user"]["is_active"] is True
    assert data["generated_id"] == 30000  # 30 * 1000


def test_create_user_invalid_age():
    """Test the /users POST endpoint with invalid age (validation should fail)"""
    invalid_event = {
        "body": json.dumps({"name": "Jane Doe", "email": "jane@example.com", "age": 200}),
        "headers": {"Content-Type": "application/json"},
        "httpMethod": "POST",
        "path": "/users",
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "1234567890",
            "httpMethod": "POST",
            "path": "/users",
            "protocol": "HTTP/1.1",
            "requestId": "test-request-id",
            "resourcePath": "/users",
            "stage": "Prod",
        },
        "resource": "/users",
    }

    ret = lambda_handler(invalid_event, lambda_context())

    # Should return 422 (Unprocessable Entity) due to validation error
    assert ret["statusCode"] == 422
