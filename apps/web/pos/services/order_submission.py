"""
POS order submission service - submits confirmed orders to POS systems.

Handles:
1. Converting internal Order to POSOrder format
2. Submitting orders to the appropriate POS adapter
3. Updating Order with POS order ID
4. Failure handling with retry logic
5. Saga pattern compensation (refund on permanent failure)
"""

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from consult_schemas import (
    POSCredentials,
    POSOrder,
    POSOrderItem,
    POSOrderItemModifier,
    POSProvider,
)

from apps.web.pos.adapters import get_adapter
from apps.web.pos.exceptions import POSAPIError, POSAuthError, POSOrderError

if TYPE_CHECKING:
    from apps.web.restaurant.models import Order, RestaurantProfile


logger = logging.getLogger(__name__)


class OrderSubmissionError(Exception):
    """Error during order submission to POS."""

    def __init__(
        self,
        message: str,
        order_id: int | None = None,
        is_retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.order_id = order_id
        self.is_retryable = is_retryable


def build_pos_order(order: "Order") -> POSOrder:
    """
    Convert internal Order model to POSOrder format.

    Args:
        order: Django Order model with related items loaded.

    Returns:
        POSOrder ready for submission to POS adapter.
    """
    from apps.web.restaurant.models import Modifier  # noqa: PLC0415

    items: list[POSOrderItem] = []

    for order_item in order.items.select_related("menu_item"):
        # Build modifiers from snapshot
        modifiers: list[POSOrderItemModifier] = []
        for mod_data in order_item.modifiers:
            # Get external_id from modifier if available
            modifier_id = mod_data.get("modifier_id")
            if modifier_id:
                try:
                    modifier = Modifier.objects.get(pk=modifier_id)
                    modifiers.append(
                        POSOrderItemModifier(
                            external_id=modifier.external_id or str(modifier_id),
                            name=mod_data.get("modifier_name", ""),
                            price_adjustment=Decimal(
                                mod_data.get("price_adjustment", "0")
                            ),
                        )
                    )
                except Modifier.DoesNotExist:
                    # Use snapshot data if modifier no longer exists
                    modifiers.append(
                        POSOrderItemModifier(
                            external_id=str(modifier_id),
                            name=mod_data.get("modifier_name", ""),
                            price_adjustment=Decimal(
                                mod_data.get("price_adjustment", "0")
                            ),
                        )
                    )

        items.append(
            POSOrderItem(
                menu_item_external_id=order_item.menu_item.external_id
                or str(order_item.menu_item.pk),
                name=order_item.item_name,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                modifiers=modifiers,
                special_instructions=order_item.special_instructions,
            )
        )

    # Map order type
    from consult_schemas import OrderType  # noqa: PLC0415

    order_type = (
        OrderType.PICKUP if order.order_type == "pickup" else OrderType.DELIVERY
    )

    return POSOrder(
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        order_type=order_type,
        scheduled_time=order.scheduled_time,
        special_instructions=order.special_instructions,
        items=items,
        subtotal=order.subtotal,
        tax=order.tax,
        tip=order.tip,
        total=order.total,
    )


def get_pos_credentials(profile: "RestaurantProfile") -> POSCredentials | None:
    """
    Get POS credentials for a restaurant from Doppler.

    In production, credentials are stored per-client in Doppler.
    For development/demo mode, we return mock credentials.

    Args:
        profile: RestaurantProfile with POS provider info.

    Returns:
        POSCredentials if available, None for demo/mock mode.
    """
    from django.conf import settings  # noqa: PLC0415

    if not profile.has_pos:
        return None

    # Map provider string to enum
    provider_map = {
        "toast": POSProvider.TOAST,
        "clover": POSProvider.CLOVER,
        "square": POSProvider.SQUARE,
    }
    provider = provider_map.get(profile.pos_provider)
    if not provider:
        return None

    # Get credentials from settings (injected from Doppler)
    # Format: POS_{PROVIDER}_{CLIENT_SLUG}_CLIENT_ID, etc.
    client_slug = profile.client.slug.upper().replace("-", "_")
    prefix = f"POS_{profile.pos_provider.upper()}_{client_slug}"

    client_id = getattr(settings, f"{prefix}_CLIENT_ID", None)
    client_secret = getattr(settings, f"{prefix}_CLIENT_SECRET", None)

    if not client_id or not client_secret:
        # Demo mode - return None to trigger mock/placeholder behavior
        logger.info(
            "No POS credentials found for %s/%s - using placeholder mode",
            profile.client.slug,
            profile.pos_provider,
        )
        return None

    return POSCredentials(
        provider=provider,
        client_id=client_id,
        client_secret=client_secret,
        location_id=profile.pos_location_id,
    )


async def _submit_order_async(
    order: "Order",
    profile: "RestaurantProfile",
) -> tuple[str, str | None, datetime | None]:
    """
    Async implementation of order submission.

    Returns:
        Tuple of (external_id, confirmation_code, estimated_ready_time)
    """
    from consult_schemas import POSProvider as POSProviderEnum  # noqa: PLC0415

    # Build POS order
    pos_order = build_pos_order(order)

    # Get adapter (always works - uses placeholder mode if no credentials)
    provider_map = {
        "toast": POSProviderEnum.TOAST,
        "clover": POSProviderEnum.CLOVER,
        "square": POSProviderEnum.SQUARE,
    }
    provider = provider_map.get(profile.pos_provider, POSProviderEnum.MOCK)
    adapter = get_adapter(provider)

    # Get credentials (may be None for demo mode)
    credentials = get_pos_credentials(profile)

    # Authenticate if we have credentials
    session = None
    if credentials:
        try:
            session = await adapter.authenticate(credentials)
        except POSAuthError as e:
            logger.warning("POS authentication failed, using placeholder mode: %s", e)
            # Fall through to placeholder mode

    # Create a mock session for placeholder mode
    if session is None:
        from datetime import timedelta  # noqa: PLC0415

        from consult_schemas import POSSession  # noqa: PLC0415

        session = POSSession(
            provider=provider,
            access_token="placeholder-token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    # Submit order
    result = await adapter.create_order(
        session,
        profile.pos_location_id,
        pos_order,
    )

    return (
        result.external_id,
        result.confirmation_code,
        result.estimated_ready_time,
    )


def submit_order_to_pos(order_id: int) -> dict[str, str | None]:
    """
    Submit a confirmed order to the POS system.

    This is the main entry point for order submission. It:
    1. Loads the order and validates it's ready for submission
    2. Gets the POS adapter and credentials
    3. Builds the POS order format
    4. Submits to the POS system
    5. Updates the order with the POS order ID

    Args:
        order_id: ID of the Order to submit.

    Returns:
        Dict with external_id and confirmation_code.

    Raises:
        OrderSubmissionError: If submission fails.
    """
    from apps.web.restaurant.models import Order, RestaurantProfile  # noqa: PLC0415

    # Load order
    try:
        order = (
            Order.objects.select_related("client")
            .prefetch_related("items", "items__menu_item")
            .get(pk=order_id)
        )
    except Order.DoesNotExist as e:
        raise OrderSubmissionError(
            f"Order {order_id} not found",
            order_id=order_id,
            is_retryable=False,
        ) from e

    # Check order is ready for submission
    if order.external_id:
        logger.info(
            "Order %s already submitted (external_id=%s)",
            order_id,
            order.external_id,
        )
        return {
            "external_id": order.external_id,
            "confirmation_code": order.confirmation_code,
        }

    if order.status not in ("confirmed", "pending"):
        raise OrderSubmissionError(
            f"Order {order_id} is not ready for submission (status={order.status})",
            order_id=order_id,
            is_retryable=False,
        )

    # Get restaurant profile
    try:
        profile = RestaurantProfile.objects.get(client=order.client)
    except RestaurantProfile.DoesNotExist:
        # No POS configured - mark as confirmed without external_id
        logger.info(
            "No restaurant profile for order %s - marking as confirmed without POS",
            order_id,
        )
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return {
            "external_id": None,
            "confirmation_code": order.confirmation_code,
        }

    if not profile.has_pos:
        # No POS configured - mark as confirmed without external_id
        logger.info(
            "No POS configured for order %s - marking as confirmed without POS",
            order_id,
        )
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return {
            "external_id": None,
            "confirmation_code": order.confirmation_code,
        }

    # Submit to POS
    try:
        external_id, pos_confirmation, estimated_ready = asyncio.run(
            _submit_order_async(order, profile)
        )

        # Update order with POS response
        with transaction.atomic():
            order.external_id = external_id
            order.status = "confirmed"
            order.submitted_at = timezone.now()

            # Use POS confirmation code if provided, keep ours otherwise
            if pos_confirmation and not order.confirmation_code:
                order.confirmation_code = pos_confirmation

            if estimated_ready:
                order.estimated_ready_time = estimated_ready

            order.save(
                update_fields=[
                    "external_id",
                    "status",
                    "submitted_at",
                    "confirmation_code",
                    "estimated_ready_time",
                ]
            )

        logger.info(
            "Order %s submitted to POS: external_id=%s",
            order_id,
            external_id,
        )

        return {
            "external_id": external_id,
            "confirmation_code": order.confirmation_code,
        }

    except (POSAPIError, POSOrderError) as e:
        logger.error("POS submission failed for order %s: %s", order_id, e)
        raise OrderSubmissionError(
            str(e),
            order_id=order_id,
            is_retryable=True,
        ) from e


def handle_pos_submission_failure(
    order_id: int,
    error: str,
    auto_refund: bool = False,
) -> None:
    """
    Handle permanent POS submission failure.

    Called after all retry attempts are exhausted.

    Args:
        order_id: ID of the failed order.
        error: Error message describing the failure.
        auto_refund: If True, automatically refund the payment.
    """
    from apps.web.restaurant.models import Order  # noqa: PLC0415

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.error("Order %s not found for failure handling", order_id)
        return

    with transaction.atomic():
        order.status = "pos_failed"
        order.save(update_fields=["status"])

        logger.error(
            "Order %s permanently failed POS submission: %s",
            order_id,
            error,
        )

        # TODO: Send notification to restaurant staff when notification
        # task is implemented.

        if auto_refund and order.stripe_payment_intent_id:
            compensate_failed_order(order)


def compensate_failed_order(order: "Order") -> bool:
    """
    Saga compensation: Refund payment for failed POS submission.

    Args:
        order: The Order to refund.

    Returns:
        True if refund was successful, False otherwise.
    """
    from apps.web.payments.services import PaymentError, create_refund  # noqa: PLC0415

    if order.payment_status not in ("captured", "succeeded"):
        logger.info(
            "Order %s payment status is %s - no refund needed",
            order.pk,
            order.payment_status,
        )
        return False

    if not order.stripe_payment_intent_id:
        logger.error("Order %s has no payment intent ID", order.pk)
        return False

    try:
        create_refund(order.stripe_payment_intent_id)

        order.payment_status = "refunded"
        order.status = "cancelled"
        order.save(update_fields=["payment_status", "status"])

        logger.info("Refunded order %s due to POS submission failure", order.pk)

        # TODO: Send customer notification
        # send_order_cancelled_notification.delay(
        #     order.pk,
        #     reason="We were unable to process your order with the restaurant. "
        #            "A full refund has been issued.",
        # )

        return True

    except PaymentError as e:
        logger.error(
            "Failed to refund order %s: %s",
            order.pk,
            e,
        )
        return False
