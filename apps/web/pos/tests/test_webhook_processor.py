"""Tests for POS webhook processing service."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient
from django.test import override_settings

import pytest

from apps.web.pos.exceptions import POSWebhookError
from apps.web.pos.models import POSWebhookEvent, WebhookStatus
from apps.web.pos.services import process_pending_webhooks, process_webhook
from apps.web.restaurant.models import RestaurantProfile
from apps.web.restaurant.tests.factories import (
    ClientFactory,
    MenuItemFactory,
    ModifierFactory,
    RestaurantProfileFactory,
)


@pytest.fixture
def client():
    """Create a test client with restaurant profile."""
    client = ClientFactory(slug="test-restaurant")
    RestaurantProfileFactory(client=client, pos_provider="toast")
    return client


@pytest.fixture
def menu_item(client):
    """Create a test menu item with external_id."""
    return MenuItemFactory(
        client=client,
        external_id="item-123",
        is_available=True,
    )


@pytest.fixture
def modifier(client):
    """Create a test modifier with external_id."""
    return ModifierFactory(
        client=client,
        external_id="mod-456",
        is_available=True,
    )


def _create_webhook_payload(event_type: str, **kwargs) -> dict:
    """Create a mock webhook payload."""
    return {
        "event_type": event_type,
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(UTC).isoformat(),
        **kwargs,
    }


def _create_signature(payload_bytes: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for webhook."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


@pytest.mark.django_db
class TestPOSWebhookEvent:
    """Tests for POSWebhookEvent model."""

    def test_create_webhook_event(self, client):
        """Test creating a webhook event."""
        event = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload={"item_id": "123", "is_available": False},
            signature="test-signature",
        )

        assert event.id is not None
        assert event.status == WebhookStatus.PENDING
        assert event.processed_at is None
        assert event.error == ""

    def test_unique_constraint(self, client):
        """Test that duplicate external_event_ids are rejected."""
        POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="test",
            payload={},
            external_event_id="event-123",
        )

        # Same client + provider + event_id should fail
        with pytest.raises(Exception):  # noqa: B017
            POSWebhookEvent.objects.create(
                client=client,
                provider="toast",
                event_type="test",
                payload={},
                external_event_id="event-123",
            )

    def test_empty_event_id_allowed_duplicates(self, client):
        """Test that empty external_event_ids allow duplicates."""
        POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="test",
            payload={},
            external_event_id="",
        )
        # Should succeed
        POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="test",
            payload={},
            external_event_id="",
        )
        assert POSWebhookEvent.objects.filter(client=client).count() == 2


@pytest.mark.django_db
class TestWebhookProcessing:
    """Tests for webhook processing service."""

    def test_process_availability_change(self, client, menu_item):
        """Test processing an item availability change webhook."""
        payload = _create_webhook_payload(
            "item_availability_changed",
            item_id=menu_item.external_id,
            is_available=False,
        )

        webhook = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload=payload,
        )

        process_webhook(str(webhook.id))

        # Reload webhook
        webhook.refresh_from_db()
        assert webhook.status == WebhookStatus.PROCESSED
        assert webhook.processed_at is not None
        assert webhook.processing_duration_ms is not None

        # Check item was updated
        menu_item.refresh_from_db()
        assert menu_item.is_available is False

    def test_process_modifier_availability_change(self, client, modifier):
        """Test processing a modifier availability change webhook."""
        payload = _create_webhook_payload(
            "item_availability_changed",
            item_id=modifier.external_id,
            is_available=False,
        )

        webhook = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload=payload,
        )

        process_webhook(str(webhook.id))

        # Check modifier was updated
        modifier.refresh_from_db()
        assert modifier.is_available is False

    def test_process_already_processed_webhook(self, client):
        """Test that already processed webhooks are skipped."""
        payload = _create_webhook_payload("item_availability_changed")

        webhook = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload=payload,
            status=WebhookStatus.PROCESSED,
        )

        # Should not raise, should just return
        process_webhook(str(webhook.id))

    @override_settings(POS_TOAST_WEBHOOK_SECRET="test-secret")
    def test_process_webhook_with_invalid_signature(self, client):
        """Test that invalid signatures fail processing."""
        payload = _create_webhook_payload("item_availability_changed")

        webhook = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload=payload,
            signature="invalid-signature",
        )

        # Should fail with secret configured
        with pytest.raises(POSWebhookError):
            process_webhook(str(webhook.id))

        webhook.refresh_from_db()
        assert webhook.status == WebhookStatus.FAILED
        assert "Invalid webhook signature" in webhook.error

    def test_process_pending_webhooks(self, client, menu_item):
        """Test processing multiple pending webhooks."""
        # Create multiple webhooks
        for i in range(3):
            payload = _create_webhook_payload(
                "item_availability_changed",
                item_id=menu_item.external_id,
                is_available=(i % 2 == 0),
            )
            POSWebhookEvent.objects.create(
                client=client,
                provider="toast",
                event_type="item_availability_changed",
                payload=payload,
            )

        processed = process_pending_webhooks(limit=10)
        assert processed == 3

        # All should be processed
        pending = POSWebhookEvent.objects.filter(status=WebhookStatus.PENDING).count()
        assert pending == 0

    def test_menu_updated_event(self, client):
        """Test handling menu updated event (logs but no action)."""
        payload = _create_webhook_payload(
            "menu_updated",
            menu_id="menu-123",
        )

        webhook = POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="menu_updated",
            payload=payload,
        )

        # Should process successfully (just logs)
        process_webhook(str(webhook.id))

        webhook.refresh_from_db()
        assert webhook.status == WebhookStatus.PROCESSED


@pytest.mark.django_db
class TestSyncAvailabilityEndpoint:
    """Tests for the manual sync availability endpoint."""

    def test_sync_requires_auth(self, client):
        """Test that sync endpoint requires authentication."""
        test_client = DjangoTestClient()
        response = test_client.post(f"/api/clients/{client.slug}/sync-availability")

        # Should redirect to login
        assert response.status_code == 302

    def test_sync_with_staff_user(self, client):
        """Test that staff users can trigger sync."""
        User = get_user_model()
        User.objects.create_user(
            username="staff",
            password="test123",
            is_staff=True,
        )

        test_client = DjangoTestClient()
        test_client.login(username="staff", password="test123")

        # Create a pending webhook
        payload = _create_webhook_payload("item_availability_changed")
        POSWebhookEvent.objects.create(
            client=client,
            provider="toast",
            event_type="item_availability_changed",
            payload=payload,
        )

        response = test_client.post(f"/api/clients/{client.slug}/sync-availability")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "sync_complete"
        assert data["webhooks_processed"] == 1

    def test_sync_no_pos_configured(self, client):
        """Test sync returns error when no POS is configured."""
        # Remove POS configuration
        RestaurantProfile.objects.filter(client=client).update(pos_provider="")

        User = get_user_model()
        User.objects.create_user(
            username="staff2",
            password="test123",
            is_staff=True,
        )

        test_client = DjangoTestClient()
        test_client.login(username="staff2", password="test123")

        response = test_client.post(f"/api/clients/{client.slug}/sync-availability")
        assert response.status_code == 400
        assert "No POS provider configured" in response.json()["error"]
