#!/usr/bin/env python3
"""
API Client for IAM-Authenticated AWS API Gateway Endpoints

This script makes signed requests to API Gateway endpoints that require
AWS IAM authorization. It automatically uses your AWS credentials from
the environment (AWS CLI profile, IAM role, etc.)

Usage:
    python scripts/call_api.py URL [options]

Examples:
    # GET request
    python scripts/call_api.py https://abc.execute-api.us-east-1.amazonaws.com/Prod/hello  # noqa: E501

    # POST with JSON body
    python scripts/call_api.py https://abc.execute-api.us-east-1.amazonaws.com/Prod/users --method POST --data '{"name":"John","email":"john@example.com"}'  # noqa: E501

    # PUT request
    python scripts/call_api.py https://abc.execute-api.us-east-1.amazonaws.com/Prod/users/123 -m PUT -d '{"name":"Jane"}'  # noqa: E501

    # DELETE request
    python scripts/call_api.py https://abc.execute-api.us-east-1.amazonaws.com/Prod/users/123 --method DELETE  # noqa: E501

Requirements:
    pip install requests requests-aws4auth boto3

For full help:
    python scripts/call_api.py --help
"""  # noqa: E501

import argparse
import json
import sys
from typing import Any
from urllib.parse import urlparse

try:
    import boto3  # type: ignore
    import requests  # type: ignore
    from requests_aws4auth import AWS4Auth  # type: ignore
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("\nInstall dependencies with:")
    print("  pip install requests requests-aws4auth boto3")
    print("  or")
    print("  pipenv install requests-aws4auth")
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


def call_api(url: str, method: str = "GET", data: str | None = None, timeout: int = 30) -> None:
    """
    Call API Gateway endpoint with IAM authentication.

    Args:
        url: Full API endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        data: JSON string for request body (for POST/PUT)
        timeout: Request timeout in seconds
    """
    method = method.upper()

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


def _create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Call IAM-authenticated AWS API Gateway endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # GET request
  %(prog)s https://abc.execute-api.us-east-1.amazonaws.com/Prod/hello

  # GET with path parameters
  %(prog)s https://abc.execute-api.us-east-1.amazonaws.com/Prod/users/123

  # POST request with JSON body
  %(prog)s https://abc.execute-api.us-east-1.amazonaws.com/Prod/users \\
    --method POST --data '{"name":"John","email":"john@example.com"}'

  # Different HTTP methods
  %(prog)s https://api.../Prod/users/123 --method PUT --data '{"name":"Jane"}'
  %(prog)s https://api.../Prod/users/123 --method DELETE

Environment:
  AWS credentials are automatically detected from:
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - AWS CLI profile (AWS_PROFILE env var or ~/.aws/credentials)
    - IAM role (if running on EC2/Lambda/ECS)
        """,
    )

    parser.add_argument(
        "url",
        help="Full API Gateway endpoint URL (e.g., https://abc.execute-api.us-east-1.amazonaws.com/Prod/hello)",  # noqa: E501
    )

    parser.add_argument(
        "-m",
        "--method",
        default="GET",
        choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        help="HTTP method (default: GET)",
    )

    parser.add_argument(
        "-d",
        "--data",
        help="JSON data for request body (for POST/PUT/PATCH)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )

    return parser


def main() -> None:
    """Parse arguments and call API."""
    parser = _create_argument_parser()
    args = parser.parse_args()
    call_api(args.url, args.method, args.data, args.timeout)


if __name__ == "__main__":
    main()
