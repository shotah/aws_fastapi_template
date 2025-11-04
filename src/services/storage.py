"""
S3 Storage Service Module

Provides a clean interface for S3 operations with proper error handling.
"""

import os
from typing import Optional

import boto3  # type: ignore
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError  # type: ignore

logger = Logger(child=True)


class StorageService:
    """Service class for S3 storage operations."""

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize the storage service.

        Args:
            bucket_name: S3 bucket name. If not provided, reads from
                        DATA_BUCKET environment variable.
        """
        self.bucket_name = bucket_name or os.getenv("DATA_BUCKET")
        if not self.bucket_name:
            raise ValueError("Bucket name must be provided or DATA_BUCKET env var must be set")
        self.s3_client = boto3.client("s3")
        logger.info(f"StorageService initialized with bucket: {self.bucket_name}")

    def upload_file(
        self,
        file_content: bytes,
        key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_content: File content as bytes
            key: S3 object key (path)
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the object

        Returns:
            S3 object key of uploaded file

        Raises:
            ClientError: If upload fails
        """
        try:
            extra_args: dict[str, str | dict[str, str]] = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args,
            )
            logger.info(f"Successfully uploaded file to s3://{self.bucket_name}/{key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    def download_file(self, key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            key: S3 object key (path)

        Returns:
            File content as bytes

        Raises:
            ClientError: If download fails or object doesn't exist
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response["Body"].read()
            logger.info(f"Successfully downloaded file from s3://{self.bucket_name}/{key}")
            return content
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"File not found: s3://{self.bucket_name}/{key}")
            else:
                logger.error(f"Failed to download file from S3: {e}")
            raise

    def delete_file(self, key: str) -> None:
        """
        Delete a file from S3.

        Args:
            key: S3 object key (path)

        Raises:
            ClientError: If deletion fails
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted file from s3://{self.bucket_name}/{key}")
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise

    def list_files(self, prefix: str = "") -> list[dict[str, str]]:
        """
        List files in the bucket with optional prefix filter.

        Args:
            prefix: Optional prefix to filter objects (e.g., "uploads/")

        Returns:
            List of dictionaries with 'key', 'size', and 'last_modified' fields

        Raises:
            ClientError: If listing fails
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)

            if "Contents" not in response:
                logger.info(f"No files found in s3://{self.bucket_name}/{prefix}")
                return []

            files = [
                {
                    "key": obj["Key"],
                    "size": str(obj["Size"]),
                    "last_modified": obj["LastModified"].isoformat(),
                }
                for obj in response["Contents"]
            ]
            logger.info(f"Listed {len(files)} files from s3://{self.bucket_name}/{prefix}")
            return files
        except ClientError as e:
            logger.error(f"Failed to list files from S3: {e}")
            raise

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            key: S3 object key (path)

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            # Re-raise unexpected errors
            logger.error(f"Failed to check file existence in S3: {e}")
            raise

    def get_presigned_url(
        self, key: str, expiration: int = 3600, http_method: str = "get_object"
    ) -> str:
        """
        Generate a presigned URL for S3 object access.

        Args:
            key: S3 object key (path)
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method ('get_object' or 'put_object')

        Returns:
            Presigned URL string

        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            logger.info(f"Generated presigned URL for s3://{self.bucket_name}/{key}")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


# Singleton instance for reuse
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get or create a singleton StorageService instance.

    Returns:
        StorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
