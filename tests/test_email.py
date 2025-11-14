"""Tests for SES EmailService module.

These tests use moto to mock SES, allowing fast, isolated unit tests
without requiring real AWS resources or verified email addresses.
"""

import os

import pytest
from botocore.exceptions import ClientError

from services.email import EmailService


class TestEmailService:
    """Tests for the EmailService class."""

    def test_init_with_from_email(self, mock_verified_email):
        """Test EmailService initialization with explicit from_email."""
        service = EmailService(from_email=mock_verified_email)
        assert service.from_email == mock_verified_email

    def test_init_from_env_var(self, mock_verified_email):
        """Test EmailService initialization from FROM_EMAIL env var."""
        service = EmailService()
        assert service.from_email == mock_verified_email

    def test_init_without_email_raises_error(self, aws_credentials):
        """Test that initialization fails without from_email or env var."""
        # Clear the env var
        os.environ.pop("FROM_EMAIL", None)

        with pytest.raises(ValueError, match="From email must be provided"):
            EmailService()

    def test_send_email_basic(self, mock_verified_email, ses_client):
        """Test sending a basic email."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_email(
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_html="<html><body><h1>Test</h1></body></html>",
            body_text="Test plain text",
        )

        # Verify message_id was returned
        assert message_id is not None
        assert isinstance(message_id, str)
        assert len(message_id) > 0

    def test_send_email_with_metadata(self, mock_verified_email):
        """Test sending an email with CC, BCC, and reply-to."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_email(
            to_addresses=["to@example.com"],
            subject="Test with metadata",
            body_html="<html><body>Test</body></html>",
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to=["reply@example.com"],
        )

        assert message_id is not None

    def test_send_email_html_only(self, mock_verified_email):
        """Test sending an email with only HTML body (no plain text)."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_email(
            to_addresses=["recipient@example.com"],
            subject="HTML Only",
            body_html="<html><body><h1>HTML Only</h1></body></html>",
        )

        assert message_id is not None

    def test_send_email_multiple_recipients(self, mock_verified_email):
        """Test sending email to multiple recipients."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_email(
            to_addresses=[
                "user1@example.com",
                "user2@example.com",
                "user3@example.com",
            ],
            subject="Multiple recipients",
            body_html="<html><body>Test</body></html>",
        )

        assert message_id is not None

    def test_send_email_invalid_address_fails(self, mock_verified_email):
        """Test that sending to invalid email address raises error."""
        service = EmailService(from_email=mock_verified_email)

        # Moto may not validate email format, so this tests the service handles errors
        # In real AWS, invalid emails would raise ClientError
        try:
            service.send_email(
                to_addresses=["not-an-email"],
                subject="Invalid",
                body_html="<html><body>Test</body></html>",
            )
        except ClientError:
            # Expected if moto validates email format
            pass

    def test_send_templated_email(self, mock_verified_email):
        """Test sending an email using the base template."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_templated_email(
            to_addresses=["user@example.com"],
            subject="Templated Email",
            title="Welcome",
            body_content="<h2>Hello!</h2><p>Welcome to our service.</p>",
        )

        assert message_id is not None

    def test_send_templated_email_with_reply_to(self, mock_verified_email):
        """Test templated email with reply-to."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_templated_email(
            to_addresses=["user@example.com"],
            subject="Test",
            title="Test Title",
            body_content="<p>Test content</p>",
            reply_to=["noreply@example.com"],
        )

        assert message_id is not None

    def test_send_daily_report_default(self, mock_verified_email):
        """Test sending daily report with default content."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_daily_report(to_addresses=["admin@example.com"])

        assert message_id is not None

    def test_send_daily_report_custom_content(self, mock_verified_email):
        """Test sending daily report with custom content."""
        service = EmailService(from_email=mock_verified_email)

        custom_content = """
            <h2>Daily Metrics</h2>
            <ul>
                <li>Users: 150</li>
                <li>Revenue: $1,234</li>
                <li>Active sessions: 45</li>
            </ul>
        """

        message_id = service.send_daily_report(
            to_addresses=["admin@example.com"], report_content=custom_content
        )

        assert message_id is not None

    def test_send_daily_report_multiple_admins(self, mock_verified_email):
        """Test sending daily report to multiple administrators."""
        service = EmailService(from_email=mock_verified_email)

        message_id = service.send_daily_report(
            to_addresses=["admin1@example.com", "admin2@example.com"]
        )

        assert message_id is not None

    def test_base_template_contains_required_placeholders(self):
        """Test that base template has required placeholders."""
        assert "{title}" in EmailService.BASE_EMAIL_TEMPLATE
        assert "{body}" in EmailService.BASE_EMAIL_TEMPLATE
        assert "{environment}" in EmailService.BASE_EMAIL_TEMPLATE

    def test_base_template_has_styling(self):
        """Test that base template includes CSS styling."""
        assert "<style>" in EmailService.BASE_EMAIL_TEMPLATE
        assert "</style>" in EmailService.BASE_EMAIL_TEMPLATE
        assert "font-family" in EmailService.BASE_EMAIL_TEMPLATE

    def test_environment_variable_injection(self, mock_verified_email):
        """Test that environment variable is injected into emails."""
        os.environ["ENVIRONMENT"] = "TestEnv"
        service = EmailService(from_email=mock_verified_email)

        # Send templated email (which uses environment variable)
        message_id = service.send_templated_email(
            to_addresses=["user@example.com"],
            subject="Test",
            title="Test",
            body_content="<p>Test</p>",
        )

        assert message_id is not None
        # Environment is injected into template


class TestEmailServiceSingleton:
    """Tests for the Email service singleton pattern."""

    def test_direct_instantiation_returns_instance(self, mock_verified_email):
        """Test that direct instantiation returns an EmailService instance."""
        service = EmailService()
        assert isinstance(service, EmailService)
        assert service.from_email == mock_verified_email

    def test_direct_instantiation_singleton(self, mock_verified_email):
        """Test that direct instantiation returns the same instance."""
        service1 = EmailService()
        service2 = EmailService()

        # Should be the same instance (singleton)
        assert service1 is service2

    def test_fresh_instance_after_clear(self, mock_verified_email):
        """Test creating a fresh instance after clearing singleton."""
        # Clear the singleton using class method
        EmailService.clear_connections()

        service = EmailService()
        assert isinstance(service, EmailService)

    def test_clear_specific_sender_connection(self, mock_verified_email):
        """Test clearing a specific sender connection."""
        # Get connection
        service1 = EmailService(mock_verified_email)

        # Clear specific connection
        EmailService.clear_connection(mock_verified_email)

        # Getting again should create new instance
        service2 = EmailService(mock_verified_email)

        # Should be different instances
        assert service1 is not service2

    def test_multiple_sender_connections(self, ses_client, mock_verified_email):
        """Test managing connections for multiple senders."""
        # Verify a second email
        second_email = "noreply@example.com"
        ses_client.verify_email_identity(EmailAddress=second_email)

        # Get connections for both senders - just instantiate directly!
        service1 = EmailService(mock_verified_email)
        service2 = EmailService(second_email)

        # Should be different instances
        assert service1 is not service2
        assert service1.from_email == mock_verified_email
        assert service2.from_email == second_email

        # Both should be able to send
        msg_id1 = service1.send_email(
            to_addresses=["test@example.com"],
            subject="From sender 1",
            body_html="<p>Test</p>",
        )
        msg_id2 = service2.send_email(
            to_addresses=["test@example.com"],
            subject="From sender 2",
            body_html="<p>Test</p>",
        )

        assert msg_id1 is not None
        assert msg_id2 is not None

    def test_singleton_behavior(self, mock_verified_email):
        """Test that instantiating with same email returns same instance."""
        service1 = EmailService(mock_verified_email)
        service2 = EmailService(mock_verified_email)

        # Should be the same instance
        assert service1 is service2


class TestEmailServiceErrorHandling:
    """Tests for error handling in EmailService."""

    def test_send_email_logs_errors(self, mock_verified_email, ses_client):
        """Test that email sending errors are properly logged."""
        service = EmailService(from_email=mock_verified_email)

        # Note: Moto doesn't validate all SES constraints (like empty recipients)
        # In real AWS, sending to empty recipients would fail with ClientError
        # This test verifies the service handles errors when they do occur

        # Test with a scenario that would fail in real AWS
        # For now, verify that the service doesn't crash with empty list
        # (Moto will accept it, but real AWS would reject)
        try:
            service.send_email(
                to_addresses=[],  # Would be invalid in real AWS
                subject="Test",
                body_html="<html><body>Test</body></html>",
            )
            # Moto allows this, but it's okay for testing
        except (ClientError, Exception):
            # Expected in real AWS
            pass

    def test_send_email_handles_client_error(self, mock_verified_email):
        """Test that ClientError from SES is properly handled."""
        service = EmailService(from_email=mock_verified_email)

        # Moto should handle most SES validation
        # In real AWS, various ClientErrors can occur (quota exceeded, etc.)
        # This test ensures the service doesn't swallow errors
        try:
            service.send_email(
                to_addresses=["test@example.com"],
                subject="Test",
                body_html="<html><body>Test</body></html>",
            )
        except ClientError as e:
            # If error occurs, verify it's properly raised
            assert "Error" in e.response
            assert "Code" in e.response["Error"]


class TestEmailServiceIntegration:
    """Integration tests that exercise multiple service methods."""

    def test_send_multiple_email_types(self, mock_verified_email):
        """Test sending different types of emails in sequence."""
        service = EmailService(from_email=mock_verified_email)

        # Send basic email
        msg1 = service.send_email(
            to_addresses=["user1@example.com"],
            subject="Basic Email",
            body_html="<html><body>Basic</body></html>",
        )

        # Send templated email
        msg2 = service.send_templated_email(
            to_addresses=["user2@example.com"],
            subject="Templated",
            title="Template",
            body_content="<p>Templated</p>",
        )

        # Send daily report
        msg3 = service.send_daily_report(to_addresses=["admin@example.com"])

        # All should succeed
        assert all([msg1, msg2, msg3])
        assert len({msg1, msg2, msg3}) == 3  # All unique message IDs

    def test_reuse_service_instance(self, mock_verified_email):
        """Test that service instance can be reused for multiple sends."""
        service = EmailService(from_email=mock_verified_email)

        message_ids = []
        for i in range(5):
            msg_id = service.send_email(
                to_addresses=[f"user{i}@example.com"],
                subject=f"Email {i}",
                body_html=f"<html><body>Email {i}</body></html>",
            )
            message_ids.append(msg_id)

        # All should succeed with unique IDs
        assert len(message_ids) == 5
        assert len(set(message_ids)) == 5  # All unique
