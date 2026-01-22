"""
Inbox services - SMS/Email sending via external providers.
"""

import logging

from django.conf import settings

import resend
from twilio.rest import Client as TwilioClient  # type: ignore[import-untyped]

from apps.web.core.models import Client

logger = logging.getLogger(__name__)


class SMSError(Exception):
    """Raised when SMS sending fails."""

    pass


class EmailError(Exception):
    """Raised when email sending fails."""

    pass


def send_sms(client: Client, to_phone: str, body: str) -> str:
    """
    Send SMS via Twilio.

    Args:
        client: The Client sending the SMS (provides Twilio phone number)
        to_phone: Recipient phone number
        body: Message text

    Returns:
        Twilio message SID

    Raises:
        SMSError: If sending fails or client has no Twilio phone configured
    """
    if not client.twilio_phone:
        raise SMSError(f"Client {client.slug} has no Twilio phone configured")

    if not to_phone:
        raise SMSError("Recipient phone number is required")

    if not body:
        raise SMSError("Message body is required")

    # Get Twilio credentials from settings
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)

    if not account_sid or not auth_token:
        raise SMSError("Twilio credentials not configured")

    try:
        twilio = TwilioClient(account_sid, auth_token)

        message = twilio.messages.create(
            body=body,
            from_=client.twilio_phone,
            to=to_phone,
        )

        logger.info(
            "Sent SMS to %s from %s (SID: %s)",
            to_phone,
            client.twilio_phone,
            message.sid,
        )

        return str(message.sid)

    except Exception as e:
        logger.exception("Failed to send SMS to %s: %s", to_phone, e)
        raise SMSError(f"Failed to send SMS: {e}") from e


def send_email(
    client: Client,
    to_email: str,
    subject: str,
    body: str,
    reply_to_message_id: str = "",
) -> str:
    """
    Send email via Resend.

    Args:
        client: The Client sending the email (used for from address)
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        reply_to_message_id: Optional Message-ID for threading replies

    Returns:
        Resend email ID

    Raises:
        EmailError: If sending fails
    """
    if not to_email:
        raise EmailError("Recipient email address is required")

    if not subject:
        raise EmailError("Email subject is required")

    if not body:
        raise EmailError("Email body is required")

    # Get Resend API key from settings
    api_key = getattr(settings, "RESEND_API_KEY", None)
    if not api_key:
        raise EmailError("Resend API key not configured")

    resend.api_key = api_key

    # Build from address using client slug
    from_address = f"{client.name} <reply@{client.slug}.consult.io>"

    try:
        email_params: dict[str, str | dict[str, str]] = {
            "from": from_address,
            "to": to_email,
            "subject": subject,
            "text": body,
        }

        # Add threading header if replying to a message
        if reply_to_message_id:
            email_params["headers"] = {"In-Reply-To": reply_to_message_id}

        response = resend.Emails.send(email_params)  # type: ignore[arg-type]

        email_id = response.get("id", "") if isinstance(response, dict) else ""

        logger.info(
            "Sent email to %s from %s (ID: %s)",
            to_email,
            from_address,
            email_id,
        )

        return str(email_id)

    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to_email, e)
        raise EmailError(f"Failed to send email: {e}") from e
