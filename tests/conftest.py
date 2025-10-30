"""Pytest configuration and fixtures."""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Add src directory to Python path for test imports
# This allows tests to import modules the same way Lambda does
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class MockLambdaContext:
    """Mock Lambda context object for testing.

    Mimics the aws_lambda_powertools.utilities.typing.LambdaContext interface.
    """

    def __init__(
        self,
        function_name: str = "test-func",
        memory_limit_in_mb: int = 128,
        invoked_function_arn: str = "arn:aws:lambda:eu-west-1:809313241234:function:test-func",
        aws_request_id: str = "52fdfc07-2182-154f-163f-5f0f9a621d72",
    ) -> None:
        self.function_name = function_name
        self.memory_limit_in_mb = memory_limit_in_mb
        self.invoked_function_arn = invoked_function_arn
        self.aws_request_id = aws_request_id

    def get_remaining_time_in_millis(self) -> int:
        """Return mock remaining time in milliseconds."""
        return 1000


@pytest.fixture()
def lambda_context() -> MockLambdaContext:
    """Provide a mock Lambda context for testing."""
    return MockLambdaContext()


@pytest.fixture()
def base_apigw_event() -> dict[str, Any]:
    """Loads base API Gateway event from JSON fixture file.

    Returns a fresh copy each time to prevent test contamination.
    """
    fixture_path = Path(__file__).parent / "fixtures" / "apigw_hello_event.json"
    with open(fixture_path) as f:
        event = json.load(f)
    # Return a deep copy to prevent fixture mutation between tests
    return copy.deepcopy(event)
