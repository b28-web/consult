"""
Process pending submissions into Contact + Message records.

Usage:
    doppler run -- uv run python apps/web/manage.py process_submissions
    doppler run -- uv run python apps/web/manage.py process_submissions --once
    doppler run -- uv run python apps/web/manage.py process_submissions \\
        --skip-classification
"""

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.web.core.models import Client
from apps.web.inbox.models import Contact, Message, Submission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process pending submissions into Contact + Message records"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process once and exit (default: poll every 30s)",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Polling interval in seconds (default: 30)",
        )
        parser.add_argument(
            "--skip-classification",
            action="store_true",
            help="Skip AI classification (useful for testing)",
        )

    def handle(self, *_args: Any, **options: Any) -> None:
        once = options["once"]
        interval = options["interval"]
        self.skip_classification = options["skip_classification"]

        self.stdout.write("Starting submission processor...")
        if self.skip_classification:
            self.stdout.write("  (AI classification disabled)")

        while True:
            processed, errors = self.process_pending()

            if processed or errors:
                self.stdout.write(f"Processed {processed} submissions, {errors} errors")

            if once:
                break

            time.sleep(interval)

    def process_pending(self) -> tuple[int, int]:
        """Process all pending submissions. Returns (processed_count, error_count)."""
        pending = Submission.objects.filter(processed_at__isnull=True).select_related(
            "message"
        )

        processed = 0
        errors = 0

        for submission in pending:
            try:
                self.process_one(submission)
                processed += 1
            except Exception as e:
                errors += 1
                logger.exception("Error processing submission %s: %s", submission.id, e)
                submission.error = str(e)
                submission.save(update_fields=["error"])

        return processed, errors

    @transaction.atomic
    def process_one(self, submission: Submission) -> Message:
        """Process a single submission into a Contact + Message."""
        # Look up client by slug
        try:
            client = Client.objects.get(slug=submission.client_slug)
        except Client.DoesNotExist as e:
            raise ValueError(f"Unknown client slug: {submission.client_slug}") from e

        # Extract fields from payload
        payload = submission.payload
        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip().lower()
        phone = self._normalize_phone(payload.get("phone", ""))
        body = payload.get("message", "") or payload.get("body", "")
        subject = payload.get("subject", "")

        # Validate: need at least email or phone
        if not email and not phone:
            raise ValueError("Submission has no email or phone")

        # Find or create contact
        contact = self._find_or_create_contact(
            client=client,
            email=email,
            phone=phone,
            name=name,
        )

        # Map channel string to enum
        channel = self._map_channel(submission.channel)

        # Create message
        message = Message.objects.create(
            client=client,
            contact=contact,
            channel=channel,
            direction=Message.Direction.INBOUND,
            subject=subject,
            body=body,
            source_url=submission.source_url,
        )

        # Update contact stats
        contact.message_count += 1
        contact.last_message_at = message.received_at
        contact.save(update_fields=["message_count", "last_message_at"])

        # Mark submission as processed
        submission.message = message
        submission.processed_at = timezone.now()
        submission.save(update_fields=["message", "processed_at"])

        logger.info(
            "Processed submission %s -> message %s for contact %s",
            submission.id,
            message.id,
            contact.id,
        )

        # Run AI classification (outside transaction, non-blocking)
        if not self.skip_classification:
            self._classify_message(message, contact, client)

        return message

    def _classify_message(
        self, message: Message, contact: Contact, client: Client
    ) -> None:
        """
        Run AI classification on a message and update fields.

        Classification errors are logged but don't fail the submission.
        """
        try:
            from baml_client import b  # noqa: PLC0415
            from baml_client.types import MessageClassification  # noqa: PLC0415, TC002

            result: MessageClassification = b.ClassifyMessage(
                message_content=message.body,
                message_source=message.channel,
                client_vertical=client.vertical,
            )

            # Store classification results on message
            message.category = result.category.value
            message.intent = result.intent.value
            message.urgency = str(result.urgency)
            message.suggested_action = result.suggested_action.value
            message.ai_confidence = result.confidence
            message.ai_summary = result.summary
            message.is_new_lead = result.is_new_lead
            message.save(
                update_fields=[
                    "category",
                    "intent",
                    "urgency",
                    "suggested_action",
                    "ai_confidence",
                    "ai_summary",
                    "is_new_lead",
                ]
            )

            # Enrich contact with extracted info
            self._enrich_contact_from_classification(contact, result)

            logger.info(
                "Classified message %s: category=%s, intent=%s, urgency=%s",
                message.id,
                result.category.value,
                result.intent.value,
                result.urgency,
            )

        except Exception as e:
            # Classification failures should not fail the submission
            logger.warning(
                "Classification failed for message %s: %s",
                message.id,
                e,
            )

    def _enrich_contact_from_classification(
        self,
        contact: Contact,
        classification: Any,  # MessageClassification
    ) -> None:
        """
        Update contact with any info extracted by AI classification.

        Only updates fields that are currently empty.
        """
        updated_fields: list[str] = []

        # Update name if empty and extracted
        if not contact.name and classification.extracted_name:
            contact.name = classification.extracted_name
            updated_fields.append("name")

        # Update email if empty and extracted
        if not contact.email and classification.extracted_email:
            contact.email = classification.extracted_email.lower()
            updated_fields.append("email")

        # Update phone if empty and extracted
        if not contact.phone and classification.extracted_phone:
            contact.phone = self._normalize_phone(classification.extracted_phone)
            updated_fields.append("phone")

        # Update address if empty and extracted
        if not contact.address and classification.extracted_address:
            contact.address = classification.extracted_address
            updated_fields.append("address")

        if updated_fields:
            contact.save(update_fields=updated_fields)
            logger.info(
                "Enriched contact %s with extracted fields: %s",
                contact.id,
                ", ".join(updated_fields),
            )

    def _find_or_create_contact(
        self,
        client: Client,
        email: str,
        phone: str,
        name: str,
    ) -> Contact:
        """
        Find or create a contact by email (primary) or phone (fallback).

        If contact exists, update name if provided and current name is empty.
        """
        contact = None

        # Try email first (primary identifier)
        if email:
            contact = Contact.objects.filter(client=client, email=email).first()

        # Fall back to phone
        if not contact and phone:
            contact = Contact.objects.filter(client=client, phone=phone).first()

        if contact:
            # Update name if we have a better one
            if name and not contact.name:
                contact.name = name
                contact.save(update_fields=["name"])
            return contact

        # Create new contact
        return Contact.objects.create(
            client=client,
            name=name or email or phone,  # Default name to identifier
            email=email,
            phone=phone,
        )

    def _normalize_phone(self, phone: str | None) -> str:
        """Normalize phone number - strip non-digits, keep basic format."""
        if not phone:
            return ""
        # Remove common formatting characters
        digits = "".join(c for c in phone if c.isdigit())
        if not digits:
            return ""
        # Add + prefix for international if 11+ digits (US: 1 + 10)
        if len(digits) >= 11 and not digits.startswith("+"):
            return f"+{digits}"
        return digits

    def _map_channel(self, channel: str) -> str:
        """Map submission channel string to Message.Channel enum value."""
        channel_lower = channel.lower()
        channel_map = {
            "form": Message.Channel.FORM,
            "sms": Message.Channel.SMS,
            "voicemail": Message.Channel.VOICEMAIL,
            "email": Message.Channel.EMAIL,
        }
        if channel_lower not in channel_map:
            raise ValueError(f"Unknown channel: {channel}")
        return channel_map[channel_lower]
