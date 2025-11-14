"""
SQS Queue Service Module

Provides a clean interface for SQS operations with proper error handling.
"""

import os
from typing import Any, Optional

import boto3  # type: ignore
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError  # type: ignore

logger = Logger(child=True)

# Module-level storage for queue connections (singleton pattern)
_queue_connections: dict[str, "SQSService"] = {}


class SQSService:
    """Service class for SQS operations.

    Manages connections to SQS queues. Automatically caches connections
    per queue URL to optimize Lambda cold starts and resource usage.

    Usage:
        # Automatically returns singleton per queue
        queue = SQSService("https://sqs.us-east-1.amazonaws.com/123456789/my-queue")
        same_queue = SQSService("https://sqs.us-east-1.amazonaws.com/123456789/my-queue")
        assert queue is same_queue

        # Different queue = different instance
        other_queue = SQSService("https://sqs.us-east-1.amazonaws.com/123456789/other-queue")
        assert queue is not other_queue
    """

    def __new__(cls, queue_url: Optional[str] = None):
        """
        Control instance creation to implement singleton pattern per queue.

        Returns existing instance if queue connection already exists.
        """
        # Resolve queue URL
        resolved_url = queue_url or os.getenv("SQS_QUEUE_URL")
        if not resolved_url:
            raise ValueError("Queue URL must be provided or SQS_QUEUE_URL env var must be set")

        # Return existing connection if it exists
        if resolved_url in _queue_connections:
            return _queue_connections[resolved_url]

        # Create new instance and cache it
        instance = super().__new__(cls)
        _queue_connections[resolved_url] = instance
        return instance

    def __init__(self, queue_url: Optional[str] = None):
        """
        Initialize the SQS service for a specific queue.

        Note: Due to singleton pattern, __init__ may be called multiple times
        on the same instance. We guard against re-initialization.

        Args:
            queue_url: SQS queue URL. If not provided, reads from
                      SQS_QUEUE_URL environment variable.
        """
        # Only initialize once (singleton may call __init__ multiple times)
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.queue_url = queue_url or os.getenv("SQS_QUEUE_URL")
        self.sqs_client = boto3.client("sqs")
        logger.info(f"SQSService initialized with queue: {self.queue_url}")

    @classmethod
    def clear_connections(cls) -> None:
        """
        Clear all cached queue connections.

        Useful for testing or when you need to force reconnection.

        Example:
            # In test teardown
            SQSService.clear_connections()
        """
        _queue_connections.clear()
        logger.info("Cleared all SQS queue connections")

    @classmethod
    def clear_connection(cls, queue_url: str) -> None:
        """
        Clear a specific queue connection.

        Args:
            queue_url: URL of the queue connection to clear

        Example:
            SQSService.clear_connection("https://sqs.us-east-1.amazonaws.com/123/my-queue")
        """
        if queue_url in _queue_connections:
            # Remove the _initialized flag before deleting so it can be recreated fresh
            if hasattr(_queue_connections[queue_url], "_initialized"):
                delattr(_queue_connections[queue_url], "_initialized")
            del _queue_connections[queue_url]
            logger.info(f"Cleared SQS connection for queue: {queue_url}")

    def send_message(
        self,
        message_body: str,
        message_attributes: Optional[dict[str, Any]] = None,
        delay_seconds: int = 0,
        message_group_id: Optional[str] = None,
        message_deduplication_id: Optional[str] = None,
    ) -> str:
        """
        Send a message to the SQS queue.

        Args:
            message_body: The message body (string, JSON, etc.)
            message_attributes: Optional message attributes
            delay_seconds: Delay before message becomes available (0-900 seconds)
            message_group_id: Required for FIFO queues
            message_deduplication_id: Optional deduplication ID for FIFO queues

        Returns:
            Message ID of the sent message

        Raises:
            ClientError: If send operation fails
        """
        try:
            kwargs: dict[str, Any] = {
                "QueueUrl": self.queue_url,
                "MessageBody": message_body,
                "DelaySeconds": delay_seconds,
            }

            if message_attributes:
                kwargs["MessageAttributes"] = message_attributes

            if message_group_id:
                kwargs["MessageGroupId"] = message_group_id

            if message_deduplication_id:
                kwargs["MessageDeduplicationId"] = message_deduplication_id

            response = self.sqs_client.send_message(**kwargs)
            message_id = response["MessageId"]
            logger.info(f"Successfully sent message {message_id} to {self.queue_url}")
            return message_id
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}")
            raise

    def send_message_batch(
        self, messages: list[dict[str, Any]], max_batch_size: int = 10
    ) -> dict[str, Any]:
        """
        Send multiple messages to the SQS queue in a single request.

        Args:
            messages: List of message dictionaries. Each must have 'Id' and 'MessageBody'.
                     Optional keys: 'DelaySeconds', 'MessageAttributes', 'MessageGroupId',
                     'MessageDeduplicationId'
            max_batch_size: Maximum messages per batch (default 10, SQS limit)

        Returns:
            Dictionary with 'Successful' and 'Failed' lists

        Raises:
            ValueError: If more than max_batch_size messages provided
            ClientError: If batch send operation fails
        """
        if len(messages) > max_batch_size:
            raise ValueError(f"Batch send supports maximum {max_batch_size} messages")

        try:
            response = self.sqs_client.send_message_batch(
                QueueUrl=self.queue_url,
                Entries=messages,
            )
            successful = len(response.get("Successful", []))
            failed = len(response.get("Failed", []))
            logger.info(
                f"Batch sent {successful} messages successfully, {failed} failed to {self.queue_url}"
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to batch send messages to SQS: {e}")
            raise

    def receive_messages(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: Optional[int] = None,
        message_attribute_names: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Receive messages from the SQS queue.

        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)
            visibility_timeout: How long messages are hidden from other consumers
            message_attribute_names: List of attribute names to receive (or ['All'])

        Returns:
            List of message dictionaries

        Raises:
            ClientError: If receive operation fails
        """
        try:
            kwargs: dict[str, Any] = {
                "QueueUrl": self.queue_url,
                "MaxNumberOfMessages": min(max_messages, 10),  # SQS max is 10
                "WaitTimeSeconds": wait_time_seconds,
            }

            if visibility_timeout is not None:
                kwargs["VisibilityTimeout"] = visibility_timeout

            if message_attribute_names:
                kwargs["MessageAttributeNames"] = message_attribute_names

            response = self.sqs_client.receive_message(**kwargs)
            messages = response.get("Messages", [])
            logger.info(f"Received {len(messages)} messages from {self.queue_url}")
            return messages
        except ClientError as e:
            logger.error(f"Failed to receive messages from SQS: {e}")
            raise

    def delete_message(self, receipt_handle: str) -> None:
        """
        Delete a message from the SQS queue.

        Args:
            receipt_handle: Receipt handle of the message to delete

        Raises:
            ClientError: If delete operation fails
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.info(f"Successfully deleted message from {self.queue_url}")
        except ClientError as e:
            logger.error(f"Failed to delete message from SQS: {e}")
            raise

    def delete_message_batch(self, receipt_handles: list[str]) -> dict[str, Any]:
        """
        Delete multiple messages from the SQS queue.

        Args:
            receipt_handles: List of receipt handles to delete (max 10)

        Returns:
            Dictionary with 'Successful' and 'Failed' lists

        Raises:
            ValueError: If more than 10 receipt handles provided
            ClientError: If batch delete operation fails
        """
        if len(receipt_handles) > 10:
            raise ValueError("Batch delete supports maximum 10 messages")

        try:
            entries = [
                {"Id": str(i), "ReceiptHandle": handle} for i, handle in enumerate(receipt_handles)
            ]
            response = self.sqs_client.delete_message_batch(
                QueueUrl=self.queue_url,
                Entries=entries,
            )
            successful = len(response.get("Successful", []))
            failed = len(response.get("Failed", []))
            logger.info(
                f"Batch deleted {successful} messages successfully, {failed} failed from {self.queue_url}"
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to batch delete messages from SQS: {e}")
            raise

    def change_message_visibility(self, receipt_handle: str, visibility_timeout: int) -> None:
        """
        Change the visibility timeout of a message.

        Args:
            receipt_handle: Receipt handle of the message
            visibility_timeout: New visibility timeout in seconds (0-43200)

        Raises:
            ClientError: If operation fails
        """
        try:
            self.sqs_client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout,
            )
            logger.info(f"Changed message visibility to {visibility_timeout}s in {self.queue_url}")
        except ClientError as e:
            logger.error(f"Failed to change message visibility in SQS: {e}")
            raise

    def purge_queue(self) -> None:
        """
        Delete all messages from the queue.

        Warning: This operation is irreversible. Use with caution.

        Raises:
            ClientError: If purge operation fails
        """
        try:
            self.sqs_client.purge_queue(QueueUrl=self.queue_url)
            logger.warning(f"Purged all messages from queue: {self.queue_url}")
        except ClientError as e:
            logger.error(f"Failed to purge queue: {e}")
            raise

    def get_queue_attributes(self, attribute_names: Optional[list[str]] = None) -> dict[str, str]:
        """
        Get attributes of the queue.

        Args:
            attribute_names: List of attribute names to retrieve, or ['All']

        Returns:
            Dictionary of queue attributes

        Raises:
            ClientError: If operation fails
        """
        try:
            kwargs: dict[str, Any] = {"QueueUrl": self.queue_url}
            if attribute_names:
                kwargs["AttributeNames"] = attribute_names
            else:
                kwargs["AttributeNames"] = ["All"]

            response = self.sqs_client.get_queue_attributes(**kwargs)
            attributes = response.get("Attributes", {})
            logger.info(f"Retrieved {len(attributes)} attributes from {self.queue_url}")
            return attributes
        except ClientError as e:
            logger.error(f"Failed to get queue attributes: {e}")
            raise

    def get_approximate_message_count(self) -> int:
        """
        Get the approximate number of messages in the queue.

        Returns:
            Approximate message count

        Raises:
            ClientError: If operation fails
        """
        attributes = self.get_queue_attributes(["ApproximateNumberOfMessages"])
        count = int(attributes.get("ApproximateNumberOfMessages", 0))
        logger.info(f"Queue {self.queue_url} has approximately {count} messages")
        return count
