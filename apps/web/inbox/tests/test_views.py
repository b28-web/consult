"""
Tests for inbox views.
"""

from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient
from django.urls import reverse

import pytest

from apps.web.core.models import Client as ClientModel
from apps.web.inbox.models import Message
from apps.web.inbox.tests.factories import ContactFactory, MessageFactory

User = get_user_model()


@pytest.fixture
def client_tenant(db) -> ClientModel:
    """Create a test client (tenant)."""
    return ClientModel.objects.create(
        slug="test-client",
        name="Test Client",
        email="test@example.com",
    )


@pytest.fixture
def user(client_tenant: ClientModel) -> User:
    """Create a test user associated with the client tenant."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        client=client_tenant,
    )


@pytest.mark.django_db
class TestInboxListView:
    """Tests for the inbox list view."""

    def test_inbox_requires_authentication(self):
        """Inbox page should redirect anonymous users to login."""
        http_client = DjangoTestClient()
        response = http_client.get(reverse("inbox:list"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_inbox_renders_for_authenticated_user(self, user, client_tenant):
        """Inbox page should render for authenticated users."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))
        assert response.status_code == 200
        assert b"Inbox" in response.content

    def test_inbox_shows_messages(self, user, client_tenant):
        """Inbox should display messages for the client."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Hello, I need help with my order.",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))

        assert response.status_code == 200
        assert contact.name.encode() in response.content

    def test_inbox_hides_other_client_messages(self, user, client_tenant):
        """Inbox should not show messages from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)
        MessageFactory(
            client=other_client,
            contact=other_contact,
            body="Secret message from other client",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))

        assert response.status_code == 200
        assert b"Secret message from other client" not in response.content

    def test_inbox_filters_by_status(self, user, client_tenant):
        """Inbox should filter messages by status."""
        contact = ContactFactory(client=client_tenant)
        unread_msg = MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Unread message",
            status=Message.Status.UNREAD,
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Read message",
            status=Message.Status.READ,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)

        # Filter for unread only
        response = http_client.get(reverse("inbox:list") + "?status=unread")
        assert response.status_code == 200
        # Unread message's contact should appear
        assert unread_msg.contact.name.encode() in response.content

    def test_inbox_filters_by_channel(self, user, client_tenant):
        """Inbox should filter messages by channel."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Form submission",
            channel=Message.Channel.FORM,
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="SMS message",
            channel=Message.Channel.SMS,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)

        # Filter for SMS only
        response = http_client.get(reverse("inbox:list") + "?channel=sms")
        assert response.status_code == 200

    def test_inbox_filters_by_urgency(self, user, client_tenant):
        """Inbox should filter messages by urgency."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Urgent message",
            urgency="urgent",
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Low priority message",
            urgency="low",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)

        # Filter for urgent only
        response = http_client.get(reverse("inbox:list") + "?urgency=urgent")
        assert response.status_code == 200

    def test_inbox_sorts_by_urgency_then_date(self, user, client_tenant):
        """Messages should be sorted by urgency (high first), then by date."""
        contact = ContactFactory(client=client_tenant)

        # Create messages in reverse order
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Low priority message",
            urgency="low",
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Urgent message",
            urgency="urgent",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))

        content = response.content.decode()
        urgent_pos = content.find("Urgent")
        low_pos = content.find("Low")

        # Urgent badge should appear before Low badge
        assert urgent_pos < low_pos, "Urgent messages should appear before low priority"

    def test_inbox_htmx_returns_partial(self, user, client_tenant):
        """HTMX requests should return just the message list partial."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(
            reverse("inbox:list"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        # Partial should not include full page structure
        assert b"<!DOCTYPE html>" not in response.content
        assert b'id="message-list"' in response.content

    def test_inbox_shows_unread_count(self, user, client_tenant):
        """Inbox should show unread message count."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Unread 1",
            status=Message.Status.UNREAD,
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Unread 2",
            status=Message.Status.UNREAD,
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Read message",
            status=Message.Status.READ,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))

        assert response.status_code == 200
        assert b"2 unread" in response.content

    def test_inbox_excludes_outbound_messages(self, user, client_tenant):
        """Inbox list should only show inbound messages."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Inbound message from customer",
            direction=Message.Direction.INBOUND,
        )
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Outbound reply to customer",
            direction=Message.Direction.OUTBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:list"))

        assert response.status_code == 200
        assert b"Outbound reply to customer" not in response.content


@pytest.mark.django_db
class TestMessageDetailView:
    """Tests for the message detail view."""

    def test_detail_requires_authentication(self, client_tenant):
        """Message detail should redirect anonymous users."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        response = http_client.get(reverse("inbox:detail", args=[message.id]))
        assert response.status_code == 302
        assert "login" in response.url

    def test_detail_renders_message(self, user, client_tenant):
        """Message detail should render the full message."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            body="This is the full message content.",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:detail", args=[message.id]))

        assert response.status_code == 200
        assert b"This is the full message content." in response.content

    def test_detail_denies_other_client_message(self, user, client_tenant):
        """Cannot view messages from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)
        other_message = MessageFactory(
            client=other_client,
            contact=other_contact,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:detail", args=[other_message.id]))

        assert response.status_code == 404

    def test_detail_shows_contact_history(self, user, client_tenant):
        """Message detail should show previous messages from same contact."""
        contact = ContactFactory(client=client_tenant)
        # Create older message
        older_message = MessageFactory(
            client=client_tenant,
            contact=contact,
            body="This is an older message from the contact.",
            direction=Message.Direction.INBOUND,
        )
        # Create current message
        current_message = MessageFactory(
            client=client_tenant,
            contact=contact,
            body="This is the current message.",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:detail", args=[current_message.id]))

        assert response.status_code == 200
        # Should show the older message in history
        assert b"This is an older message" in response.content
        # Should have "Contact History" section
        assert b"Contact History" in response.content
        # Current message should not be in history (it's the main message)
        content = response.content.decode()
        # The older message ID should be in the history for navigation
        assert f"/dashboard/inbox/{older_message.id}/" in content

    def test_detail_shows_contact_profile_link(self, user, client_tenant):
        """Message detail should link to the contact profile."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:detail", args=[message.id]))

        assert response.status_code == 200
        # Should have link to contact profile
        expected_url = reverse("crm:contact_detail", args=[contact.id])
        assert expected_url.encode() in response.content

    def test_detail_history_excludes_current_message(self, user, client_tenant):
        """Contact history should not include the current message."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Unique current message body xyz123",
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("inbox:detail", args=[message.id]))

        content = response.content.decode()
        # The message body appears once (in the main content), not in history
        # Count occurrences - should be exactly 1 (the main message body)
        assert content.count("Unique current message body xyz123") == 1


@pytest.mark.django_db
class TestMessageMarkView:
    """Tests for the message mark view."""

    def test_mark_as_read(self, user, client_tenant):
        """Should mark message as read."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            status=Message.Status.UNREAD,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("inbox:mark", args=[message.id]),
            {"status": "read"},
        )

        assert response.status_code == 200
        message.refresh_from_db()
        assert message.status == Message.Status.READ

    def test_mark_as_archived(self, user, client_tenant):
        """Should mark message as archived."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            status=Message.Status.READ,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("inbox:mark", args=[message.id]),
            {"status": "archived"},
        )

        assert response.status_code == 200
        message.refresh_from_db()
        assert message.status == Message.Status.ARCHIVED

    def test_mark_invalid_status_rejected(self, user, client_tenant):
        """Invalid status should be rejected."""
        contact = ContactFactory(client=client_tenant)
        message = MessageFactory(
            client=client_tenant,
            contact=contact,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("inbox:mark", args=[message.id]),
            {"status": "invalid"},
        )

        assert response.status_code == 400

    def test_mark_denies_other_client_message(self, user, client_tenant):
        """Cannot mark messages from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)
        other_message = MessageFactory(
            client=other_client,
            contact=other_contact,
            direction=Message.Direction.INBOUND,
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("inbox:mark", args=[other_message.id]),
            {"status": "read"},
        )

        assert response.status_code == 404
