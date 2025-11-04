"""Pytest configuration and fixtures."""

import copy
import json
import os
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import boto3  # type: ignore
import pytest
from moto import mock_aws  # type: ignore

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


# ============================================================================
# AWS Mocking Fixtures (using Moto)
# ============================================================================


@pytest.fixture(scope="function")
def aws_credentials() -> None:
    """Set fake AWS credentials for moto.

    Prevents tests from accidentally using real AWS credentials.
    Must be set before other AWS fixtures are used.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def s3_client(aws_credentials) -> Generator:
    """
    Create a mocked S3 client for testing.

    This fixture:
    - Starts moto's mock_aws context
    - Creates a boto3 S3 client
    - Yields the client for test use
    - Automatically tears down after test completes

    Usage in tests:
        def test_something(s3_client):
            # S3 operations here will be mocked
            s3_client.create_bucket(Bucket='my-bucket')
    """
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture(scope="function")
def mock_s3_bucket(s3_client) -> str:
    """
    Create a mock S3 bucket for testing.

    This fixture:
    - Uses the s3_client fixture (which starts moto mocking)
    - Creates a test bucket named "test-bucket"
    - Sets DATA_BUCKET env var (used by StorageService)
    - Returns the bucket name for test use

    Usage in tests:
        def test_storage(mock_s3_bucket):
            # StorageService will use "test-bucket"
            # All S3 operations are mocked
            storage = get_storage_service()
            storage.upload_file(...)
    """
    bucket_name = "test-bucket"
    s3_client.create_bucket(Bucket=bucket_name)

    # Set environment variable that StorageService uses
    os.environ["DATA_BUCKET"] = bucket_name

    return bucket_name
