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

    ret = lambda_handler(apigw_event, lambda_context())
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
    assert data["message"] == "hello world"
