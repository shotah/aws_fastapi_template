# Services Module

This directory contains service classes for AWS integrations and business logic.

## Available Services

### EmailService (`email.py`)

Handles all SES email operations with templating support.

**Features:**
- Base HTML email template with CSS styling
- Templated emails with content injection
- Daily report emails with default content
- Full control over recipients, CC, BCC, reply-to
- Proper error handling and logging

**Usage:**
```python
from services import get_email_service

email_service = get_email_service()

# Send templated email
email_service.send_templated_email(
    to_addresses=["user@example.com"],
    subject="Welcome!",
    title="Welcome to Our Service",
    body_content="<h2>Hello!</h2><p>Welcome message</p>"
)

# Send daily report (with default content)
email_service.send_daily_report(to_addresses=["admin@example.com"])

# Send daily report (with custom content)
email_service.send_daily_report(
    to_addresses=["admin@example.com"],
    report_content="<h2>Metrics</h2><p>Your data here</p>"
)

# Send fully custom email
email_service.send_email(
    to_addresses=["user@example.com"],
    subject="Custom Email",
    body_html="<html><body>Your HTML</body></html>",
    body_text="Plain text version",
    reply_to=["noreply@example.com"]
)
```

### StorageService (`storage.py`)

Handles all S3 storage operations.

**Features:**
- Upload/download files
- List files with prefix filtering
- Delete files
- Check file existence
- Generate presigned URLs
- Proper error handling and logging

**Usage:**
```python
from services import get_storage_service

storage = get_storage_service()

# Upload file
storage.upload_file(
    file_content=b"file data",
    key="uploads/file.txt",
    content_type="text/plain"
)

# Download file
content = storage.download_file("uploads/file.txt")

# List files
files = storage.list_files(prefix="uploads/")

# Check if file exists
exists = storage.file_exists("uploads/file.txt")

# Delete file
storage.delete_file("uploads/file.txt")

# Get presigned URL
url = storage.get_presigned_url("uploads/file.txt", expiration=3600)
```

## Design Pattern

All services follow a consistent pattern:

1. **Class-based**: Each service is a class with focused methods
2. **Singleton**: Use `get_<service>_service()` to get a reusable instance
3. **Environment variables**: Configuration from env vars with defaults
4. **Logging**: Structured logging via AWS Lambda Powertools
5. **Error handling**: Proper exception handling with informative errors
6. **Type hints**: Full type annotations for better IDE support

## Adding New Services

When adding a new service:

1. Create `src/services/new_service.py`
2. Follow the pattern from `storage.py` or `email.py`
3. Add imports to `src/services/__init__.py`
4. Add to `__all__` list
5. Document usage in this README

Example structure:
```python
"""New Service Module"""

import os
from typing import Optional
import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(child=True)

class NewService:
    """Service class for new functionality."""

    def __init__(self, param: Optional[str] = None):
        self.param = param or os.getenv("PARAM")
        self.client = boto3.client("service")
        logger.info(f"NewService initialized")

    def do_something(self) -> str:
        """Do something useful."""
        try:
            # Implementation
            logger.info("Action completed")
            return "result"
        except ClientError as e:
            logger.error(f"Failed: {e}")
            raise

# Singleton
_new_service: Optional[NewService] = None

def get_new_service() -> NewService:
    global _new_service
    if _new_service is None:
        _new_service = NewService()
    return _new_service
```
