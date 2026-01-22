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
from apps.web.crm.models import Job
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
    def process_one(self, submission: Submission) -> Message | None:
        """Process a single submission into a Contact + Message (or Job for Cal.com)."""
        # Look up client by slug
        try:
            client = Client.objects.get(slug=submission.client_slug)
        except Client.DoesNotExist as e:
            raise ValueError(f"Unknown client slug: {submission.client_slug}") from e

        # Cal.com bookings create Jobs, not Messages
        if submission.channel == "calcom":
            return self._process_calcom_booking(submission, client)

        # Jobber webhooks create/update Jobs and Contacts
        if submission.channel == "jobber":
            return self._process_jobber_webhook(submission, client)

        # Extract fields from payload (channel-aware)
        payload = submission.payload
        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip().lower()
        subject = payload.get("subject", "")

        # Channel-specific field extraction
        if submission.channel == "sms":
            # SMS: phone from "from", body from "body"
            phone = self._normalize_phone(payload.get("from", ""))
            body = payload.get("body", "")
        elif submission.channel == "voicemail":
            # Voicemail: phone from "from", body from transcription
            phone = self._normalize_phone(payload.get("from", ""))
            transcription = payload.get("transcription_text", "")
            recording_url = payload.get("recording_url", "")
            if transcription:
                body = transcription
            elif recording_url:
                # Transcription pending or failed - use placeholder
                body = f"[Voicemail recording: {recording_url}]"
            else:
                body = "[Voicemail - no transcription available]"
        else:
            # Form/email: standard fields
            phone = self._normalize_phone(payload.get("phone", ""))
            body = payload.get("message", "") or payload.get("body", "")

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

    def _process_calcom_booking(
        self, submission: Submission, client: Client
    ) -> Message | None:
        """
        Process Cal.com booking webhook into Contact + Job records.

        For BOOKING_CREATED: creates or updates Job with scheduled status
        For BOOKING_RESCHEDULED: updates Job with new time
        For BOOKING_CANCELLED: updates Job status to cancelled

        Returns None since Cal.com doesn't create Messages.
        """
        payload = submission.payload
        event_type = payload.get("event_type", "")
        booking_uid = payload.get("booking_uid", "")

        if not booking_uid:
            raise ValueError("Cal.com webhook missing booking_uid")

        # Extract attendee info
        attendee_name = payload.get("attendee_name", "").strip()
        attendee_email = payload.get("attendee_email", "").strip().lower()
        attendee_timezone = payload.get("attendee_timezone", "")

        if not attendee_email:
            raise ValueError("Cal.com webhook missing attendee_email")

        # Parse datetime strings
        from datetime import datetime  # noqa: PLC0415

        start_str = payload["start_time"].replace("Z", "+00:00")
        end_str = payload["end_time"].replace("Z", "+00:00")
        start_time = datetime.fromisoformat(start_str)
        end_time = datetime.fromisoformat(end_str)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)

        # Find or create contact by email
        contact = self._find_or_create_contact(
            client=client,
            email=attendee_email,
            phone="",
            name=attendee_name,
        )

        # Update contact timezone if provided
        if attendee_timezone and not contact.address:
            # Store timezone in address field as placeholder
            # TODO: Add proper timezone field to Contact model
            pass

        if event_type == "BOOKING_CANCELLED":
            # Find and cancel existing job
            job = Job.objects.filter(
                client=client, calcom_event_id=booking_uid
            ).first()

            if job:
                job.status = Job.Status.CANCELLED
                job.save(update_fields=["status"])
                logger.info(
                    "Cancelled Cal.com booking %s -> job %s",
                    booking_uid,
                    job.id,
                )
            else:
                logger.warning(
                    "Cal.com cancellation for unknown booking: %s",
                    booking_uid,
                )

        else:
            # BOOKING_CREATED or BOOKING_RESCHEDULED
            job, created = Job.objects.update_or_create(
                client=client,
                calcom_event_id=booking_uid,
                defaults={
                    "contact": contact,
                    "title": payload.get("title", "Cal.com Booking"),
                    "status": Job.Status.SCHEDULED,
                    "scheduled_at": start_time,
                    "duration_minutes": duration_minutes,
                },
            )

            action = "Created" if created else "Updated"
            logger.info(
                "%s Cal.com booking %s -> job %s for contact %s",
                action,
                booking_uid,
                job.id,
                contact.id,
            )

        # Mark submission as processed (no message created for Cal.com)
        submission.processed_at = timezone.now()
        submission.save(update_fields=["processed_at"])

        return None

    def _process_jobber_webhook(
        self, submission: Submission, client: Client
    ) -> Message | None:
        """
        Process Jobber webhook into Contact + Job records.

        For job.created/updated: creates or updates Job
        For job.completed: updates Job status to completed
        For client.created/updated: creates or updates Contact

        Returns None since Jobber doesn't create Messages.
        """
        payload = submission.payload
        event = payload.get("event", "")
        jobber_id = payload.get("jobber_id", "")

        if not jobber_id:
            raise ValueError("Jobber webhook missing jobber_id")

        # Handle client events (Contact creation/update)
        if event.startswith("client."):
            self._process_jobber_client(submission, client, payload)
            return None

        # Handle job events
        client_name = payload.get("client_name", "").strip()
        client_email = payload.get("client_email", "").strip().lower()
        client_phone = self._normalize_phone(payload.get("client_phone", ""))

        # Find or create contact if we have client info
        contact = None
        if client_email or client_phone:
            contact = self._find_or_create_contact(
                client=client,
                email=client_email,
                phone=client_phone,
                name=client_name,
            )

        # Map Jobber status to our Job.Status
        status_map = {
            "scheduled": Job.Status.SCHEDULED,
            "in_progress": Job.Status.IN_PROGRESS,
            "requires_invoicing": Job.Status.COMPLETED,
            "complete": Job.Status.COMPLETED,
        }
        jobber_status = payload.get("status", "scheduled").lower()
        job_status = status_map.get(jobber_status, Job.Status.SCHEDULED)

        # Parse scheduled_at if provided
        scheduled_at = None
        if payload.get("scheduled_at"):
            from datetime import datetime  # noqa: PLC0415

            scheduled_str = payload["scheduled_at"].replace("Z", "+00:00")
            scheduled_at = datetime.fromisoformat(scheduled_str)

        # Create or update job
        defaults: dict[str, object] = {
            "title": payload.get("title", "Jobber Job"),
            "status": job_status,
        }
        if contact:
            defaults["contact"] = contact
        if scheduled_at:
            defaults["scheduled_at"] = scheduled_at
        if payload.get("address"):
            defaults["address"] = payload["address"]

        job, created = Job.objects.update_or_create(
            client=client,
            jobber_id=jobber_id,
            defaults=defaults,
        )

        action = "Created" if created else "Updated"
        logger.info(
            "%s Jobber job %s -> job %s",
            action,
            jobber_id,
            job.id,
        )

        # Mark submission as processed
        submission.processed_at = timezone.now()
        submission.save(update_fields=["processed_at"])

        return None

    def _process_jobber_client(
        self,
        submission: Submission,
        client: Client,
        payload: dict[str, object],
    ) -> None:
        """Process Jobber client event into Contact record."""
        client_name = str(payload.get("client_name", "")).strip()
        client_email = str(payload.get("client_email", "")).strip().lower()
        client_phone = self._normalize_phone(str(payload.get("client_phone", "")))
        jobber_id = str(payload.get("jobber_id", ""))

        if not client_email and not client_phone:
            logger.warning("Jobber client webhook has no email or phone")
            submission.processed_at = timezone.now()
            submission.save(update_fields=["processed_at"])
            return None

        # Find or create contact
        contact = self._find_or_create_contact(
            client=client,
            email=client_email,
            phone=client_phone,
            name=client_name,
        )

        logger.info(
            "Processed Jobber client %s -> contact %s",
            jobber_id,
            contact.id,
        )

        # Mark submission as processed
        submission.processed_at = timezone.now()
        submission.save(update_fields=["processed_at"])

        return None
