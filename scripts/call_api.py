#!/usr/bin/env python3
"""
API Client for IAM-Authenticated AWS API Gateway Endpoints

This script makes signed requests to API Gateway endpoints that require
AWS IAM authorization. It reads configuration from a .env file, making it
easy to test different endpoints by just editing the .env file.

Usage:
    1. Copy .env.example to .env
    2. Edit .env with your API endpoint and request details
    3. Run: python scripts/call_api.py

Example .env:
    API_URL=https://abc.execute-api.us-east-1.amazonaws.com/Dev/hello
    API_METHOD=GET
    API_DATA=

    # For POST requests:
    # API_URL=https://abc.execute-api.us-east-1.amazonaws.com/Dev/users
    # API_METHOD=POST
    # API_DATA={"name":"John","email":"john@example.com","age":30}

Requirements:
    pip install requests requests-aws4auth boto3 python-dotenv
    or
    pipenv install
"""  # noqa: E501

import json
import os
import sys
from typing import Any
from urllib.parse import urlparse

try:
    import boto3  # type: ignore
    import requests  # type: ignore
    from dotenv import load_dotenv  # type: ignore
    from requests_aws4auth import AWS4Auth  # type: ignore
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("\nInstall dependencies with:")
    print("  pipenv install")
    sys.exit(1)


def get_aws_auth(api_url: str) -> AWS4Auth:
    """
    Create AWS SigV4 auth object using current AWS credentials.

    Args:
        api_url: Full API Gateway URL (used to extract region)

    Returns:
        AWS4Auth object for signing requests
    """
    # Get AWS credentials from environment (CLI profile, IAM role, etc.)
    session = boto3.Session()
    credentials = session.get_credentials()

    if not credentials:
        print("❌ Error: No AWS credentials found!")
        print("\nConfigure credentials using one of:")
        print("  - aws configure")
        print("  - AWS_PROFILE environment variable")
        print("  - IAM role (if running on EC2/Lambda/ECS)")
        sys.exit(1)

    # Extract region from API URL
    # Format: https://api-id.execute-api.REGION.amazonaws.com/stage/path
    parsed_url = urlparse(api_url)
    hostname = parsed_url.hostname or ""
    hostname_parts = hostname.split(".")
    if len(hostname_parts) >= 3 and hostname_parts[1] == "execute-api":
        region = hostname_parts[2]
    else:
        # Fallback to default region
        region = session.region_name or "us-east-1"
        print("⚠️  Warning: Could not extract region from URL, using: " + region)

    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        "execute-api",
        session_token=credentials.token,
    )


def call_api() -> None:
    """
    Call API Gateway endpoint with IAM authentication using .env configuration.
    """
    # Load .env file
    load_dotenv()

    # Read configuration from environment
    url = os.getenv("API_URL")
    method = os.getenv("API_METHOD", "GET").upper()
    data = os.getenv("API_DATA")
    timeout = int(os.getenv("API_TIMEOUT", "30"))

    # Validate required config
    if not url:
        print("❌ Error: API_URL not set in .env file")
        print("\nCreate a .env file with:")
        print("  API_URL=https://your-api.execute-api.region.amazonaws.com/" "stage/path")
        print("  API_METHOD=GET")
        print("  API_DATA=")
        print("\nSee .env.example for a full example")
        sys.exit(1)

    print("\n🔐 Making signed " + method + " request to:")
    print("   " + url + "\n")

    # Get AWS authentication
    auth = get_aws_auth(url)

    # Prepare request body
    json_data = _parse_json_data(data, method)

    # Make request
    response = _make_request(url, method, auth, json_data, timeout)

    # Print and exit
    _print_response(response)
    sys.exit(0 if response.ok else 1)


def _parse_json_data(data: str | None, method: str) -> dict[str, Any] | None:
    """Parse JSON data for request body."""
    if not data or method not in ["POST", "PUT", "PATCH"]:
        return None

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        print("❌ Error: Invalid JSON data: " + str(e))
        sys.exit(1)


def _make_request(
    url: str,
    method: str,
    auth: AWS4Auth,
    json_data: dict[str, Any] | None,
    timeout: int,
) -> requests.Response:
    """Make the authenticated request to API Gateway."""
    headers = {"Content-Type": "application/json"}

    try:
        return requests.request(
            method=method,
            url=url,
            auth=auth,
            headers=headers,
            json=json_data,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        print("❌ Error making request: " + str(e))
        sys.exit(1)


def _print_response(response: requests.Response) -> None:
    """Print the API response."""
    print("📥 Response Status: " + str(response.status_code))
    print("📥 Response Headers:")
    for key, value in response.headers.items():
        if key.lower() in [
            "content-type",
            "content-length",
            "x-amzn-requestid",
            "x-amzn-trace-id",
        ]:
            print("   " + key + ": " + value)

    print("\n📄 Response Body:")
    try:
        # Try to pretty-print JSON
        response_json = response.json()
        print(json.dumps(response_json, indent=2))
    except json.JSONDecodeError:
        # If not JSON, print as-is
        print(response.text)


def main() -> None:
    """Load .env and call API."""
    call_api()


if __name__ == "__main__":
    main()
