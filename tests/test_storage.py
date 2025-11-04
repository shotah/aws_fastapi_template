"""Tests for S3 StorageService module.

These tests use moto to mock S3, allowing fast, isolated unit tests
without requiring real AWS resources.
"""

import pytest
from botocore.exceptions import ClientError

from services.storage import StorageService, get_storage_service


class TestStorageService:
    """Tests for the StorageService class."""

    def test_init_with_bucket_name(self, mock_s3_bucket):
        """Test StorageService initialization with explicit bucket name."""
        service = StorageService(bucket_name=mock_s3_bucket)
        assert service.bucket_name == mock_s3_bucket

    def test_init_from_env_var(self, mock_s3_bucket):
        """Test StorageService initialization from DATA_BUCKET env var."""
        service = StorageService()
        assert service.bucket_name == mock_s3_bucket

    def test_init_without_bucket_raises_error(self, aws_credentials):
        """Test that initialization fails without bucket name or env var."""
        import os

        # Clear the env var
        os.environ.pop("DATA_BUCKET", None)

        with pytest.raises(ValueError, match="Bucket name must be provided"):
            StorageService()

    def test_upload_file(self, mock_s3_bucket, s3_client):
        """Test uploading a file to S3."""
        service = StorageService(bucket_name=mock_s3_bucket)
        content = b"Hello, World!"
        key = "test/file.txt"

        result_key = service.upload_file(
            file_content=content,
            key=key,
            content_type="text/plain",
            metadata={"author": "test"},
        )

        assert result_key == key

        # Verify file was uploaded
        response = s3_client.get_object(Bucket=mock_s3_bucket, Key=key)
        assert response["Body"].read() == content
        assert response["ContentType"] == "text/plain"
        assert response["Metadata"] == {"author": "test"}

    def test_download_file(self, mock_s3_bucket, s3_client):
        """Test downloading a file from S3."""
        service = StorageService(bucket_name=mock_s3_bucket)
        content = b"Test file content"
        key = "downloads/test.txt"

        # Upload file first
        s3_client.put_object(Bucket=mock_s3_bucket, Key=key, Body=content)

        # Download and verify
        downloaded = service.download_file(key)
        assert downloaded == content

    def test_download_nonexistent_file(self, mock_s3_bucket):
        """Test downloading a file that doesn't exist."""
        service = StorageService(bucket_name=mock_s3_bucket)

        with pytest.raises(ClientError) as exc_info:
            service.download_file("nonexistent/file.txt")

        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_delete_file(self, mock_s3_bucket, s3_client):
        """Test deleting a file from S3."""
        service = StorageService(bucket_name=mock_s3_bucket)
        key = "delete/me.txt"

        # Upload file first
        s3_client.put_object(Bucket=mock_s3_bucket, Key=key, Body=b"delete me")

        # Delete it
        service.delete_file(key)

        # Verify it's gone
        with pytest.raises(ClientError) as exc_info:
            s3_client.get_object(Bucket=mock_s3_bucket, Key=key)
        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_list_files_empty(self, mock_s3_bucket):
        """Test listing files in an empty bucket."""
        service = StorageService(bucket_name=mock_s3_bucket)
        files = service.list_files()
        assert files == []

    def test_list_files_with_content(self, mock_s3_bucket, s3_client):
        """Test listing files in a bucket with content."""
        service = StorageService(bucket_name=mock_s3_bucket)

        # Upload some files
        test_files = ["file1.txt", "file2.txt", "subfolder/file3.txt"]
        for file_key in test_files:
            s3_client.put_object(
                Bucket=mock_s3_bucket,
                Key=file_key,
                Body=b"test content",
            )

        # List all files
        files = service.list_files()
        assert len(files) == 3
        assert all(f["key"] in test_files for f in files)
        assert all("size" in f for f in files)
        assert all("last_modified" in f for f in files)

    def test_list_files_with_prefix(self, mock_s3_bucket, s3_client):
        """Test listing files with a prefix filter."""
        service = StorageService(bucket_name=mock_s3_bucket)

        # Upload files with different prefixes
        s3_client.put_object(Bucket=mock_s3_bucket, Key="uploads/file1.txt", Body=b"1")
        s3_client.put_object(Bucket=mock_s3_bucket, Key="uploads/file2.txt", Body=b"2")
        s3_client.put_object(Bucket=mock_s3_bucket, Key="downloads/file3.txt", Body=b"3")

        # List only uploads
        files = service.list_files(prefix="uploads/")
        assert len(files) == 2
        assert all(f["key"].startswith("uploads/") for f in files)

    def test_file_exists_true(self, mock_s3_bucket, s3_client):
        """Test file_exists returns True for existing file."""
        service = StorageService(bucket_name=mock_s3_bucket)
        key = "exists/file.txt"

        s3_client.put_object(Bucket=mock_s3_bucket, Key=key, Body=b"content")

        assert service.file_exists(key) is True

    def test_file_exists_false(self, mock_s3_bucket):
        """Test file_exists returns False for non-existent file."""
        service = StorageService(bucket_name=mock_s3_bucket)

        assert service.file_exists("does/not/exist.txt") is False

    def test_get_presigned_url(self, mock_s3_bucket, s3_client):
        """Test generating a presigned URL."""
        service = StorageService(bucket_name=mock_s3_bucket)
        key = "presigned/file.txt"

        # Upload file first
        s3_client.put_object(Bucket=mock_s3_bucket, Key=key, Body=b"content")

        # Generate presigned URL
        url = service.get_presigned_url(key, expiration=3600)

        # Verify it's a valid URL format
        assert url.startswith("https://")
        assert mock_s3_bucket in url
        assert key in url
        assert "Signature" in url  # AWS signature query parameter

    def test_get_presigned_url_for_upload(self, mock_s3_bucket):
        """Test generating a presigned URL for upload (PUT)."""
        service = StorageService(bucket_name=mock_s3_bucket)
        key = "upload/new-file.txt"

        url = service.get_presigned_url(
            key,
            expiration=1800,
            http_method="put_object",
        )

        # Verify it's a valid URL
        assert url.startswith("https://")
        assert mock_s3_bucket in url
        assert key in url


class TestStorageServiceSingleton:
    """Tests for the get_storage_service singleton function."""

    def test_get_storage_service_returns_instance(self, mock_s3_bucket):
        """Test that get_storage_service returns a StorageService instance."""
        service = get_storage_service()
        assert isinstance(service, StorageService)
        assert service.bucket_name == mock_s3_bucket

    def test_get_storage_service_singleton(self, mock_s3_bucket):
        """Test that get_storage_service returns the same instance."""
        service1 = get_storage_service()
        service2 = get_storage_service()

        # Should be the same instance (singleton)
        assert service1 is service2

    def test_get_storage_service_fresh_instance(self, mock_s3_bucket):
        """Test creating a fresh instance after clearing singleton."""
        from services import storage

        # Clear the singleton
        storage._storage_service = None

        service = get_storage_service()
        assert isinstance(service, StorageService)
