"""
Tests for inbox services (SMS, email sending).
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.web.inbox.services import EmailError, SMSError, send_email, send_sms

from .factories import ClientFactory


@pytest.mark.django_db
class TestSendSMS:
    """Tests for SMS sending service."""

    def test_send_sms_success(self) -> None:
        """Successful SMS sending should return message SID."""
        client = ClientFactory(twilio_phone="+15551234567")

        with patch("apps.web.inbox.services.TwilioClient") as mock_twilio:
            mock_message = MagicMock()
            mock_message.sid = "SM1234567890abcdef"
            mock_twilio.return_value.messages.create.return_value = mock_message

            with patch("apps.web.inbox.services.settings") as mock_settings:
                mock_settings.TWILIO_ACCOUNT_SID = "test_sid"
                mock_settings.TWILIO_AUTH_TOKEN = "test_token"

                sid = send_sms(client, "+15559876543", "Hello!")

        assert sid == "SM1234567890abcdef"
        mock_twilio.return_value.messages.create.assert_called_once_with(
            body="Hello!",
            from_="+15551234567",
            to="+15559876543",
        )

    def test_send_sms_no_client_phone(self) -> None:
        """Should raise error if client has no Twilio phone."""
        client = ClientFactory(twilio_phone="")

        with pytest.raises(SMSError, match="no Twilio phone configured"):
            send_sms(client, "+15559876543", "Hello!")

    def test_send_sms_no_recipient(self) -> None:
        """Should raise error if no recipient phone."""
        client = ClientFactory(twilio_phone="+15551234567")

        with pytest.raises(SMSError, match="Recipient phone number is required"):
            send_sms(client, "", "Hello!")

    def test_send_sms_no_body(self) -> None:
        """Should raise error if no message body."""
        client = ClientFactory(twilio_phone="+15551234567")

        with pytest.raises(SMSError, match="Message body is required"):
            send_sms(client, "+15559876543", "")

    def test_send_sms_no_credentials(self) -> None:
        """Should raise error if Twilio credentials not configured."""
        client = ClientFactory(twilio_phone="+15551234567")

        with patch("apps.web.inbox.services.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = ""
            mock_settings.TWILIO_AUTH_TOKEN = ""

            with pytest.raises(SMSError, match="Twilio credentials not configured"):
                send_sms(client, "+15559876543", "Hello!")

    def test_send_sms_api_error(self) -> None:
        """Should raise error if Twilio API fails."""
        client = ClientFactory(twilio_phone="+15551234567")

        with patch("apps.web.inbox.services.TwilioClient") as mock_twilio:
            mock_twilio.return_value.messages.create.side_effect = Exception(
                "API rate limited"
            )

            with patch("apps.web.inbox.services.settings") as mock_settings:
                mock_settings.TWILIO_ACCOUNT_SID = "test_sid"
                mock_settings.TWILIO_AUTH_TOKEN = "test_token"

                with pytest.raises(SMSError, match="Failed to send SMS"):
                    send_sms(client, "+15559876543", "Hello!")


@pytest.mark.django_db
class TestSendEmail:
    """Tests for email sending service."""

    def test_send_email_success(self) -> None:
        """Successful email sending should return email ID."""
        client = ClientFactory(slug="test-client", name="Test Client")

        with patch("apps.web.inbox.services.resend") as mock_resend:
            mock_resend.Emails.send.return_value = {"id": "email_123abc"}

            with patch("apps.web.inbox.services.settings") as mock_settings:
                mock_settings.RESEND_API_KEY = "test_api_key"

                email_id = send_email(
                    client,
                    "customer@example.com",
                    "Re: Your inquiry",
                    "Thanks for reaching out!",
                )

        assert email_id == "email_123abc"
        mock_resend.Emails.send.assert_called_once()
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert call_args["to"] == "customer@example.com"
        assert call_args["subject"] == "Re: Your inquiry"
        assert call_args["text"] == "Thanks for reaching out!"
        assert "test-client.consult.io" in call_args["from"]

    def test_send_email_with_reply_to(self) -> None:
        """Email with reply-to should include In-Reply-To header."""
        client = ClientFactory(slug="test-client")

        with patch("apps.web.inbox.services.resend") as mock_resend:
            mock_resend.Emails.send.return_value = {"id": "email_456def"}

            with patch("apps.web.inbox.services.settings") as mock_settings:
                mock_settings.RESEND_API_KEY = "test_api_key"

                send_email(
                    client,
                    "customer@example.com",
                    "Re: Question",
                    "Here's my answer",
                    reply_to_message_id="<original@example.com>",
                )

        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "headers" in call_args
        assert call_args["headers"]["In-Reply-To"] == "<original@example.com>"

    def test_send_email_no_recipient(self) -> None:
        """Should raise error if no recipient email."""
        client = ClientFactory()

        with pytest.raises(EmailError, match="Recipient email address is required"):
            send_email(client, "", "Subject", "Body")

    def test_send_email_no_subject(self) -> None:
        """Should raise error if no subject."""
        client = ClientFactory()

        with pytest.raises(EmailError, match="Email subject is required"):
            send_email(client, "test@example.com", "", "Body")

    def test_send_email_no_body(self) -> None:
        """Should raise error if no body."""
        client = ClientFactory()

        with pytest.raises(EmailError, match="Email body is required"):
            send_email(client, "test@example.com", "Subject", "")

    def test_send_email_no_api_key(self) -> None:
        """Should raise error if Resend API key not configured."""
        client = ClientFactory()

        with patch("apps.web.inbox.services.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = ""

            with pytest.raises(EmailError, match="Resend API key not configured"):
                send_email(client, "test@example.com", "Subject", "Body")

    def test_send_email_api_error(self) -> None:
        """Should raise error if Resend API fails."""
        client = ClientFactory()

        with patch("apps.web.inbox.services.resend") as mock_resend:
            mock_resend.Emails.send.side_effect = Exception("API error")

            with patch("apps.web.inbox.services.settings") as mock_settings:
                mock_settings.RESEND_API_KEY = "test_api_key"

                with pytest.raises(EmailError, match="Failed to send email"):
                    send_email(client, "test@example.com", "Subject", "Body")
