"""Pytest configuration and fixtures."""

import copy
import json
import os
import sys
from pathlib import Path

import pytest

# Add src directory to Python path for test imports
# This allows tests to import modules the same way Lambda does
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


@pytest.fixture()
def lambda_context():
    """Mock Lambda context object"""

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
def base_apigw_event():
    """Loads base API Gateway event from JSON fixture file.

    Returns a fresh copy each time to prevent test contamination.
    """
    fixture_path = Path(__file__).parent / "fixtures" / "apigw_hello_event.json"
    with open(fixture_path) as f:
        event = json.load(f)
    # Return a deep copy to prevent fixture mutation between tests
    return copy.deepcopy(event)
