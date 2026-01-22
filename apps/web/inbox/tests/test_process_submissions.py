"""
Tests for the process_submissions management command.
"""

from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

import pytest

from apps.web.core.models import Client
from apps.web.inbox.models import Contact, Message

from .factories import ClientFactory, ContactFactory, SubmissionFactory


@pytest.mark.django_db
class TestProcessSubmissions:
    """Tests for the process_submissions management command."""

    def test_processes_pending_submission(self) -> None:
        """A pending submission should be converted to Contact + Message."""
        client = ClientFactory(slug="coffee-shop")
        submission = SubmissionFactory(
            client_slug="coffee-shop",
            channel="form",
            payload={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "message": "I'd like to book a table.",
            },
            source_url="https://coffee-shop.com/contact",
        )

        call_command("process_submissions", "--once")

        # Verify submission is marked processed
        submission.refresh_from_db()
        assert submission.processed_at is not None
        assert submission.error == ""
        assert submission.message is not None

        # Verify contact was created
        contact = Contact.objects.get(client=client, email="jane@example.com")
        assert contact.name == "Jane Smith"
        assert contact.message_count == 1
        assert contact.last_message_at is not None

        # Verify message was created
        message = submission.message
        assert message.client == client
        assert message.contact == contact
        assert message.channel == Message.Channel.FORM
        assert message.direction == Message.Direction.INBOUND
        assert message.body == "I'd like to book a table."
        assert message.source_url == "https://coffee-shop.com/contact"

    def test_matches_existing_contact_by_email(self) -> None:
        """Submission with existing email should link to existing contact."""
        client = ClientFactory(slug="coffee-shop")
        existing_contact = ContactFactory(
            client=client,
            email="existing@example.com",
            name="Existing User",
            message_count=5,
        )

        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "name": "New Name",
                "email": "existing@example.com",
                "message": "Another message",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.message is not None
        assert submission.message.contact == existing_contact

        # Contact stats should be updated
        existing_contact.refresh_from_db()
        assert existing_contact.message_count == 6
        # Name should NOT be updated since contact already has a name
        assert existing_contact.name == "Existing User"

    def test_matches_existing_contact_by_phone(self) -> None:
        """Submission with existing phone should link to existing contact."""
        client = ClientFactory(slug="coffee-shop")
        existing_contact = ContactFactory(
            client=client,
            email="",
            phone="5551234567",
            name="Phone User",
        )

        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "name": "Someone",
                "phone": "555-123-4567",  # Same number, different format
                "message": "Call me back",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.message.contact == existing_contact

    def test_handles_unknown_client_slug(self) -> None:
        """Submission with unknown client slug should record error."""
        submission = SubmissionFactory(
            client_slug="nonexistent-client",
            payload={
                "name": "Test",
                "email": "test@example.com",
                "message": "Hello",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.processed_at is None
        assert "Unknown client slug" in submission.error

    def test_handles_missing_email_and_phone(self) -> None:
        """Submission without email or phone should record error."""
        ClientFactory(slug="coffee-shop")
        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "name": "Anonymous",
                "message": "No contact info provided",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.processed_at is None
        assert "no email or phone" in submission.error

    def test_handles_unknown_channel(self) -> None:
        """Submission with unknown channel should record error."""
        ClientFactory(slug="coffee-shop")
        submission = SubmissionFactory(
            client_slug="coffee-shop",
            channel="unknown_channel",
            payload={
                "email": "test@example.com",
                "message": "Test",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.processed_at is None
        assert "Unknown channel" in submission.error

    def test_skips_already_processed_submissions(self) -> None:
        """Already processed submissions should not be reprocessed."""
        client = ClientFactory(slug="coffee-shop")
        contact = ContactFactory(client=client, email="old@example.com")
        message = Message.objects.create(
            client=client,
            contact=contact,
            channel=Message.Channel.FORM,
            body="Old message",
        )

        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "old@example.com",
                "message": "Old message",
            },
            processed_at=timezone.now(),
            message=message,
        )

        # Create a new pending submission
        new_submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "new@example.com",
                "message": "New message",
            },
        )

        call_command("process_submissions", "--once")

        # Old submission should be unchanged
        submission.refresh_from_db()
        assert submission.message == message

        # New submission should be processed
        new_submission.refresh_from_db()
        assert new_submission.processed_at is not None
        assert new_submission.message.body == "New message"

    def test_normalizes_email_to_lowercase(self) -> None:
        """Email addresses should be normalized to lowercase."""
        ClientFactory(slug="coffee-shop")  # Client must exist

        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "John.Doe@EXAMPLE.COM",
                "message": "Test",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        assert submission.message.contact.email == "john.doe@example.com"

    def test_processes_multiple_submissions(self) -> None:
        """Multiple pending submissions should all be processed."""
        ClientFactory(slug="coffee-shop")

        submissions = [
            SubmissionFactory(
                client_slug="coffee-shop",
                payload={
                    "email": f"user{i}@example.com",
                    "message": f"Message {i}",
                },
            )
            for i in range(3)
        ]

        call_command("process_submissions", "--once")

        for submission in submissions:
            submission.refresh_from_db()
            assert submission.processed_at is not None

        assert Message.objects.count() == 3
        assert Contact.objects.count() == 3

    def test_updates_contact_name_if_empty(self) -> None:
        """Contact name should be updated if currently empty."""
        client = ClientFactory(slug="coffee-shop")
        existing_contact = ContactFactory(
            client=client,
            email="noname@example.com",
            name="",  # Empty name
        )

        SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "name": "Now Has Name",
                "email": "noname@example.com",
                "message": "Hello",
            },
        )

        call_command("process_submissions", "--once")

        existing_contact.refresh_from_db()
        assert existing_contact.name == "Now Has Name"


@pytest.mark.django_db
class TestClassificationIntegration:
    """Tests for AI classification in submission processing."""

    def _mock_classification(self, **overrides):
        """Create a mock classification result."""
        from baml_client.types import (  # noqa: PLC0415
            MessageCategory,
            MessageClassification,
            MessageIntent,
            SuggestedAction,
        )

        defaults = {
            "is_new_lead": True,
            "urgency": 3,
            "category": MessageCategory.QUOTE_REQUEST,
            "intent": MessageIntent.WANTS_SERVICE,
            "suggested_action": SuggestedAction.SEND_QUOTE,
            "summary": "Customer wants a quote for junk removal",
            "extracted_name": None,
            "extracted_phone": None,
            "extracted_email": None,
            "extracted_address": None,
            "confidence": 0.95,
        }
        defaults.update(overrides)
        return MessageClassification(**defaults)

    @patch("baml_client.b.ClassifyMessage")
    def test_classification_populates_message_fields(self, mock_classify) -> None:
        """Classification results should populate message AI fields."""
        from baml_client.types import (  # noqa: PLC0415
            MessageCategory,
            MessageIntent,
            SuggestedAction,
        )

        mock_classify.return_value = self._mock_classification(
            category=MessageCategory.APPOINTMENT_BOOKING,
            intent=MessageIntent.WANTS_SERVICE,
            suggested_action=SuggestedAction.BOOK_APPOINTMENT,
            urgency=4,
            confidence=0.92,
            summary="Customer wants to book an appointment",
            is_new_lead=True,
        )

        ClientFactory(slug="barber", vertical=Client.Vertical.BARBER)
        submission = SubmissionFactory(
            client_slug="barber",
            payload={
                "email": "customer@example.com",
                "message": "I'd like to book a haircut",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        message = submission.message
        assert message.category == "APPOINTMENT_BOOKING"
        assert message.intent == "WANTS_SERVICE"
        assert message.suggested_action == "BOOK_APPOINTMENT"
        assert message.urgency == "4"
        assert message.ai_confidence == 0.92
        assert message.ai_summary == "Customer wants to book an appointment"
        assert message.is_new_lead is True

    @patch("baml_client.b.ClassifyMessage")
    def test_classification_enriches_contact(self, mock_classify) -> None:
        """Classification should enrich contact with extracted info."""
        mock_classify.return_value = self._mock_classification(
            extracted_name="John Smith",
            extracted_phone="555-987-6543",
            extracted_address="456 Oak Ave, Springfield",
        )

        ClientFactory(slug="junk-hauler", vertical=Client.Vertical.JUNK_HAULER)
        submission = SubmissionFactory(
            client_slug="junk-hauler",
            payload={
                "email": "john@example.com",
                "message": "Need junk removed from 456 Oak Ave. Call 555-987-6543",
            },
        )

        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        contact = submission.message.contact

        # Name was provided in payload so shouldn't be overwritten
        # Phone should be enriched since it wasn't in payload
        # Address should be enriched
        assert contact.phone == "5559876543"  # Normalized
        assert contact.address == "456 Oak Ave, Springfield"

    @patch("baml_client.b.ClassifyMessage")
    def test_classification_does_not_overwrite_existing_contact_data(
        self, mock_classify
    ) -> None:
        """Classification should not overwrite existing contact data."""
        mock_classify.return_value = self._mock_classification(
            extracted_name="Different Name",
            extracted_email="different@example.com",
        )

        client = ClientFactory(slug="coffee-shop")
        existing_contact = ContactFactory(
            client=client,
            email="original@example.com",
            name="Original Name",
        )

        SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "original@example.com",
                "message": "Hello again",
            },
        )

        call_command("process_submissions", "--once")

        existing_contact.refresh_from_db()
        # Existing data should not be overwritten
        assert existing_contact.name == "Original Name"
        assert existing_contact.email == "original@example.com"

    @patch("baml_client.b.ClassifyMessage")
    def test_classification_failure_does_not_fail_submission(
        self, mock_classify
    ) -> None:
        """Classification API failure should not prevent submission processing."""
        mock_classify.side_effect = Exception("API error: rate limited")

        ClientFactory(slug="coffee-shop")
        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "test@example.com",
                "message": "Test message",
            },
        )

        # Should not raise - classification failure is logged but doesn't fail
        call_command("process_submissions", "--once")

        submission.refresh_from_db()
        # Submission should still be processed
        assert submission.processed_at is not None
        assert submission.error == ""
        assert submission.message is not None

        # Message should exist but without classification
        message = submission.message
        assert message.category == ""
        assert message.intent == ""
        assert message.ai_confidence is None

    def test_skip_classification_flag_skips_ai(self) -> None:
        """--skip-classification flag should skip AI classification."""
        ClientFactory(slug="coffee-shop")
        submission = SubmissionFactory(
            client_slug="coffee-shop",
            payload={
                "email": "test@example.com",
                "message": "Test message",
            },
        )

        # Use --skip-classification flag
        call_command("process_submissions", "--once", "--skip-classification")

        submission.refresh_from_db()
        # Submission should be processed
        assert submission.processed_at is not None
        assert submission.message is not None

        # Message should have no classification
        message = submission.message
        assert message.category == ""
        assert message.ai_confidence is None

    @patch("baml_client.b.ClassifyMessage")
    def test_client_vertical_passed_to_classifier(self, mock_classify) -> None:
        """Client vertical should be passed to the classifier."""
        mock_classify.return_value = self._mock_classification()

        ClientFactory(slug="junk-hauler", vertical=Client.Vertical.JUNK_HAULER)
        SubmissionFactory(
            client_slug="junk-hauler",
            payload={
                "email": "test@example.com",
                "message": "Need stuff hauled away",
            },
        )

        call_command("process_submissions", "--once")

        # Verify classifier was called with correct vertical
        mock_classify.assert_called_once()
        call_kwargs = mock_classify.call_args
        assert call_kwargs[1]["client_vertical"] == "junk_hauler"
