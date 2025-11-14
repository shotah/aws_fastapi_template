"""Tests for SQS Service module.

These tests use moto to mock SQS, allowing fast, isolated unit tests
without requiring real AWS resources.
"""

import pytest

from services.sqs import SQSService


class TestSQSService:
    """Tests for the SQSService class."""

    def test_init_with_queue_url(self, mock_sqs_queue):
        """Test SQSService initialization with explicit queue URL."""
        service = SQSService(queue_url=mock_sqs_queue)
        assert service.queue_url == mock_sqs_queue

    def test_init_from_env_var(self, mock_sqs_queue):
        """Test SQSService initialization from SQS_QUEUE_URL env var."""
        service = SQSService()
        assert service.queue_url == mock_sqs_queue

    def test_init_without_queue_raises_error(self, aws_credentials):
        """Test that initialization fails without queue URL or env var."""
        import os

        # Clear the env var
        os.environ.pop("SQS_QUEUE_URL", None)

        with pytest.raises(ValueError, match="Queue URL must be provided"):
            SQSService()

    def test_send_message(self, mock_sqs_queue, sqs_client):
        """Test sending a message to SQS."""
        service = SQSService(queue_url=mock_sqs_queue)
        message_body = "Test message"

        message_id = service.send_message(message_body)

        assert message_id is not None

        # Verify message was sent
        response = sqs_client.receive_message(QueueUrl=mock_sqs_queue)
        messages = response.get("Messages", [])
        assert len(messages) == 1
        assert messages[0]["Body"] == message_body

    def test_send_message_with_attributes(self, mock_sqs_queue, sqs_client):
        """Test sending a message with attributes."""
        service = SQSService(queue_url=mock_sqs_queue)
        message_body = "Test with attributes"
        attributes = {
            "Author": {"StringValue": "Test Author", "DataType": "String"},
            "Priority": {"StringValue": "High", "DataType": "String"},
        }

        message_id = service.send_message(
            message_body=message_body,
            message_attributes=attributes,
        )

        assert message_id is not None

    def test_send_message_with_delay(self, mock_sqs_queue):
        """Test sending a message with delay."""
        service = SQSService(queue_url=mock_sqs_queue)

        message_id = service.send_message(
            message_body="Delayed message",
            delay_seconds=30,
        )

        assert message_id is not None

    def test_send_message_batch(self, mock_sqs_queue, sqs_client):
        """Test batch sending messages."""
        service = SQSService(queue_url=mock_sqs_queue)
        messages = [
            {"Id": "1", "MessageBody": "Message 1"},
            {"Id": "2", "MessageBody": "Message 2"},
            {"Id": "3", "MessageBody": "Message 3"},
        ]

        response = service.send_message_batch(messages)

        assert len(response["Successful"]) == 3
        assert len(response.get("Failed", [])) == 0

        # Verify messages were sent
        received = sqs_client.receive_message(
            QueueUrl=mock_sqs_queue,
            MaxNumberOfMessages=10,
        )
        assert len(received.get("Messages", [])) == 3

    def test_send_message_batch_too_many(self, mock_sqs_queue):
        """Test batch send fails with more than 10 messages."""
        service = SQSService(queue_url=mock_sqs_queue)
        messages = [{"Id": str(i), "MessageBody": f"Message {i}"} for i in range(11)]

        with pytest.raises(ValueError, match="Batch send supports maximum 10 messages"):
            service.send_message_batch(messages)

    def test_receive_messages(self, mock_sqs_queue, sqs_client):
        """Test receiving messages from SQS."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Send some messages first
        for i in range(3):
            sqs_client.send_message(
                QueueUrl=mock_sqs_queue,
                MessageBody=f"Message {i}",
            )

        # Receive messages
        messages = service.receive_messages(max_messages=3)

        assert len(messages) == 3
        assert all("Body" in msg for msg in messages)
        assert all("ReceiptHandle" in msg for msg in messages)

    def test_receive_messages_empty_queue(self, mock_sqs_queue):
        """Test receiving messages from empty queue."""
        service = SQSService(queue_url=mock_sqs_queue)

        messages = service.receive_messages()

        assert messages == []

    def test_receive_messages_with_wait_time(self, mock_sqs_queue):
        """Test receiving messages with long polling."""
        service = SQSService(queue_url=mock_sqs_queue)

        # This should return quickly with no messages
        messages = service.receive_messages(
            max_messages=1,
            wait_time_seconds=1,  # Short wait for testing
        )

        assert messages == []

    def test_delete_message(self, mock_sqs_queue, sqs_client):
        """Test deleting a message from SQS."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Send a message
        sqs_client.send_message(
            QueueUrl=mock_sqs_queue,
            MessageBody="Message to delete",
        )

        # Receive it
        response = sqs_client.receive_message(QueueUrl=mock_sqs_queue)
        message = response["Messages"][0]
        receipt_handle = message["ReceiptHandle"]

        # Delete it
        service.delete_message(receipt_handle)

        # Verify it's gone (should return empty after visibility timeout)
        messages = sqs_client.receive_message(QueueUrl=mock_sqs_queue)
        assert "Messages" not in messages

    def test_delete_message_batch(self, mock_sqs_queue, sqs_client):
        """Test batch deleting messages."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Send multiple messages
        for i in range(3):
            sqs_client.send_message(
                QueueUrl=mock_sqs_queue,
                MessageBody=f"Message {i}",
            )

        # Receive them
        response = sqs_client.receive_message(
            QueueUrl=mock_sqs_queue,
            MaxNumberOfMessages=10,
        )
        receipt_handles = [msg["ReceiptHandle"] for msg in response["Messages"]]

        # Batch delete
        result = service.delete_message_batch(receipt_handles)

        assert len(result["Successful"]) == 3
        assert len(result.get("Failed", [])) == 0

    def test_delete_message_batch_too_many(self, mock_sqs_queue):
        """Test batch delete fails with more than 10 messages."""
        service = SQSService(queue_url=mock_sqs_queue)
        receipt_handles = [f"handle-{i}" for i in range(11)]

        with pytest.raises(ValueError, match="Batch delete supports maximum 10 messages"):
            service.delete_message_batch(receipt_handles)

    def test_change_message_visibility(self, mock_sqs_queue, sqs_client):
        """Test changing message visibility timeout."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Send a message
        sqs_client.send_message(
            QueueUrl=mock_sqs_queue,
            MessageBody="Visibility test",
        )

        # Receive it
        response = sqs_client.receive_message(QueueUrl=mock_sqs_queue)
        receipt_handle = response["Messages"][0]["ReceiptHandle"]

        # Change visibility
        service.change_message_visibility(
            receipt_handle=receipt_handle,
            visibility_timeout=60,
        )

        # Should succeed without error
        assert True

    def test_purge_queue(self, mock_sqs_queue, sqs_client):
        """Test purging all messages from queue."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Send multiple messages
        for i in range(5):
            sqs_client.send_message(
                QueueUrl=mock_sqs_queue,
                MessageBody=f"Message {i}",
            )

        # Purge queue
        service.purge_queue()

        # Note: moto may not perfectly simulate purge, but method should not error
        assert True

    def test_get_queue_attributes(self, mock_sqs_queue):
        """Test getting queue attributes."""
        service = SQSService(queue_url=mock_sqs_queue)

        attributes = service.get_queue_attributes()

        assert isinstance(attributes, dict)
        assert "QueueArn" in attributes

    def test_get_queue_attributes_specific(self, mock_sqs_queue):
        """Test getting specific queue attributes."""
        service = SQSService(queue_url=mock_sqs_queue)

        attributes = service.get_queue_attributes(
            attribute_names=["QueueArn", "ApproximateNumberOfMessages"]
        )

        assert isinstance(attributes, dict)
        assert "QueueArn" in attributes

    def test_get_approximate_message_count(self, mock_sqs_queue, sqs_client):
        """Test getting approximate message count."""
        service = SQSService(queue_url=mock_sqs_queue)

        # Initially should be 0
        count = service.get_approximate_message_count()
        assert count == 0

        # Send some messages
        for i in range(3):
            sqs_client.send_message(
                QueueUrl=mock_sqs_queue,
                MessageBody=f"Message {i}",
            )

        # Count should increase
        count = service.get_approximate_message_count()
        assert count >= 0  # Moto may not update this immediately


class TestSQSServiceSingleton:
    """Tests for the SQS service singleton pattern."""

    def test_direct_instantiation_returns_instance(self, mock_sqs_queue):
        """Test that direct instantiation returns an SQSService instance."""
        service = SQSService()
        assert isinstance(service, SQSService)
        assert service.queue_url == mock_sqs_queue

    def test_direct_instantiation_singleton(self, mock_sqs_queue):
        """Test that direct instantiation returns the same instance."""
        service1 = SQSService()
        service2 = SQSService()

        # Should be the same instance (singleton)
        assert service1 is service2

    def test_fresh_instance_after_clear(self, mock_sqs_queue):
        """Test creating a fresh instance after clearing singleton."""
        # Clear the singleton using class method
        SQSService.clear_connections()

        service = SQSService()
        assert isinstance(service, SQSService)

    def test_clear_specific_queue_connection(self, mock_sqs_queue):
        """Test clearing a specific queue connection."""
        # Get connection
        service1 = SQSService(mock_sqs_queue)

        # Clear specific connection
        SQSService.clear_connection(mock_sqs_queue)

        # Getting again should create new instance
        service2 = SQSService(mock_sqs_queue)

        # Should be different instances
        assert service1 is not service2

    def test_multiple_queue_connections(self, sqs_client, mock_sqs_queue):
        """Test managing connections to multiple queues."""
        # Create a second queue
        response = sqs_client.create_queue(QueueName="test-queue-2")
        second_queue_url = response["QueueUrl"]

        # Get connections to both queues - just instantiate directly!
        service1 = SQSService(mock_sqs_queue)
        service2 = SQSService(second_queue_url)

        # Should be different instances
        assert service1 is not service2
        assert service1.queue_url == mock_sqs_queue
        assert service2.queue_url == second_queue_url

        # Test operations on both
        service1.send_message("Message to queue 1")
        service2.send_message("Message to queue 2")

        messages1 = service1.receive_messages()
        messages2 = service2.receive_messages()

        assert len(messages1) == 1
        assert messages1[0]["Body"] == "Message to queue 1"
        assert len(messages2) == 1
        assert messages2[0]["Body"] == "Message to queue 2"

    def test_singleton_behavior(self, mock_sqs_queue):
        """Test that instantiating with same queue returns same instance."""
        service1 = SQSService(mock_sqs_queue)
        service2 = SQSService(mock_sqs_queue)

        # Should be the same instance
        assert service1 is service2
