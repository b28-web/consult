"""
POS webhook processor - handles incoming POS webhook events.

Processes webhooks from the pos_poswebhookevent table:
1. Verify signature
2. Parse event
3. Route to handler
4. Update database
"""

import json
import logging
import time
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderStatusChangedEvent,
)
from consult_schemas import POSWebhookEvent as POSWebhookEventSchema

from apps.web.pos.adapters.mock import MockPOSAdapter
from apps.web.pos.exceptions import POSWebhookError
from apps.web.pos.models import POSWebhookEvent, WebhookStatus
from apps.web.restaurant.models import MenuItem, Modifier

logger = logging.getLogger(__name__)


def get_adapter_for_provider(provider: str) -> MockPOSAdapter:  # noqa: ARG001
    """
    Get the POS adapter for a provider.

    Currently only MockPOSAdapter is implemented.
    Toast/Clover/Square adapters will be added in future tickets.
    """
    # For now, all providers use the mock adapter for webhook parsing
    # Real adapters will be added in 008-F, 008-G, 008-H
    return MockPOSAdapter()


def get_webhook_secret(provider: str) -> str:
    """Get the webhook secret for a provider from settings."""
    secret_map = {
        "toast": getattr(settings, "POS_TOAST_WEBHOOK_SECRET", ""),
        "clover": getattr(settings, "POS_CLOVER_WEBHOOK_SECRET", ""),
        "square": getattr(settings, "POS_SQUARE_WEBHOOK_SECRET", ""),
    }
    return secret_map.get(provider, "")


def process_pending_webhooks(limit: int = 100) -> int:
    """
    Process pending POS webhooks.

    Args:
        limit: Maximum number of webhooks to process in one batch.

    Returns:
        Number of webhooks processed.
    """
    pending = POSWebhookEvent.objects.filter(status=WebhookStatus.PENDING).order_by(
        "received_at"
    )[:limit]

    processed_count = 0
    for webhook in pending:
        try:
            process_webhook(str(webhook.id))
            processed_count += 1
        except Exception as e:
            logger.exception("Failed to process webhook %s: %s", webhook.id, e)

    return processed_count


def process_webhook(webhook_id: str) -> None:
    """
    Process a single POS webhook event.

    Args:
        webhook_id: The UUID of the webhook to process.

    Raises:
        POSWebhookError: If processing fails.
    """
    start_time = time.monotonic()
    error_to_raise: Exception | None = None

    with transaction.atomic():
        webhook = POSWebhookEvent.objects.select_for_update().get(id=webhook_id)

        # Skip if already processed
        if webhook.status != WebhookStatus.PENDING:
            logger.info(
                "Webhook %s already processed (status: %s)",
                webhook_id,
                webhook.status,
            )
            return

        try:
            adapter = get_adapter_for_provider(webhook.provider)

            # Verify signature if secret is configured
            secret = get_webhook_secret(webhook.provider)
            if secret and webhook.signature:
                payload_bytes = json.dumps(webhook.payload).encode()
                is_valid = adapter.verify_webhook_signature(
                    payload_bytes, webhook.signature, secret
                )
                if not is_valid:
                    raise POSWebhookError(
                        "Invalid webhook signature",
                        provider=webhook.provider,
                    )

            # Parse webhook event
            event = adapter.parse_webhook(webhook.payload)

            # Route to handler
            _handle_pos_event(webhook.client, event)

            # Mark as processed
            duration_ms = int((time.monotonic() - start_time) * 1000)
            webhook.status = WebhookStatus.PROCESSED
            webhook.processed_at = timezone.now()
            webhook.processing_duration_ms = duration_ms
            webhook.save(
                update_fields=["status", "processed_at", "processing_duration_ms"]
            )

            logger.info(
                "Processed webhook %s (%s:%s) in %dms",
                webhook_id,
                webhook.provider,
                webhook.event_type,
                duration_ms,
            )

        except Exception as e:
            # Mark as failed - save the error but don't re-raise yet
            # so the transaction commits the failed status
            duration_ms = int((time.monotonic() - start_time) * 1000)
            webhook.status = WebhookStatus.FAILED
            webhook.processed_at = timezone.now()
            webhook.processing_duration_ms = duration_ms
            webhook.error = str(e)
            webhook.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "processing_duration_ms",
                    "error",
                ]
            )

            logger.exception(
                "Failed to process webhook %s: %s",
                webhook_id,
                e,
            )
            error_to_raise = e

    # Re-raise outside the transaction so the failed status is committed
    if error_to_raise is not None:
        raise error_to_raise


def _handle_pos_event(client: Any, event: POSWebhookEventSchema) -> None:
    """
    Route a POS event to the appropriate handler.

    Args:
        client: The Client the event belongs to.
        event: The parsed webhook event.
    """
    if isinstance(event, ItemAvailabilityChangedEvent):
        _handle_availability_change(client, event)
    elif isinstance(event, MenuUpdatedEvent):
        _handle_menu_updated(client, event)
    elif isinstance(event, OrderStatusChangedEvent):
        _handle_order_status_change(client, event)
    else:
        logger.warning("Unhandled event type: %s", type(event).__name__)


def _handle_availability_change(
    client: Any, event: ItemAvailabilityChangedEvent
) -> None:
    """
    Handle item availability (86'd) change event.

    Updates MenuItem.is_available for the item.
    """
    updated = MenuItem.objects.filter(
        client=client,
        external_id=event.item_id,
    ).update(
        is_available=event.is_available,
        availability_updated_at=timezone.now(),
    )

    if updated:
        logger.info(
            "Updated availability for item %s: is_available=%s",
            event.item_id,
            event.is_available,
        )
    else:
        # Try to find modifier by external_id
        updated_mod = Modifier.objects.filter(
            client=client,
            external_id=event.item_id,
        ).update(is_available=event.is_available)

        if updated_mod:
            logger.info(
                "Updated availability for modifier %s: is_available=%s",
                event.item_id,
                event.is_available,
            )
        else:
            logger.warning(
                "Item/modifier not found for availability update: %s",
                event.item_id,
            )


def _handle_menu_updated(client: Any, event: MenuUpdatedEvent) -> None:
    """
    Handle menu updated event.

    For now, just logs the event. Full menu sync will be implemented
    when we have POS API access to fetch the updated menu.
    """
    logger.info(
        "Menu updated for client %s: menu_id=%s (full sync not implemented)",
        client.slug,
        event.menu_id,
    )
    # TODO: Trigger full menu sync when POS adapters support get_menu()
    # This requires async API calls which will be added in 008-F


def _handle_order_status_change(client: Any, event: OrderStatusChangedEvent) -> None:
    """
    Handle order status change event.

    Updates Order.status for the order.
    """
    from apps.web.restaurant.models import Order  # noqa: PLC0415

    updated = Order.objects.filter(
        client=client,
        external_id=event.order_id,
    ).update(status=event.status.value)

    if updated:
        logger.info(
            "Updated order %s status: %s -> %s",
            event.order_id,
            event.previous_status,
            event.status,
        )
    else:
        logger.warning(
            "Order not found for status update: %s",
            event.order_id,
        )
