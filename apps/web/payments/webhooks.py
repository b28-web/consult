"""
Stripe webhook handlers.

Handles payment events from Stripe:
- payment_intent.succeeded: Payment completed, update order status
- payment_intent.payment_failed: Payment failed, notify customer
"""

import logging
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import stripe

from apps.web.restaurant.models import Order, OrderStatus, PaymentStatus

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """
    Handle Stripe webhook events.

    POST /payments/webhooks/stripe

    Events handled:
    - payment_intent.succeeded: Order confirmed
    - payment_intent.payment_failed: Payment failed
    """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", "")

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.warning("Invalid Stripe webhook payload: %s", e)
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Invalid Stripe webhook signature: %s", e)
        return HttpResponse("Invalid signature", status=400)

    # Log event for debugging
    logger.info("Received Stripe event: %s", event["type"])

    # Route to handler
    match event["type"]:
        case "payment_intent.succeeded":
            _handle_payment_succeeded(event["data"]["object"])
        case "payment_intent.payment_failed":
            _handle_payment_failed(event["data"]["object"])
        case _:
            logger.debug("Ignoring unhandled Stripe event: %s", event["type"])

    return HttpResponse(status=200)


def _handle_payment_succeeded(payment_intent: dict[str, object]) -> None:
    """
    Update order status when payment succeeds.

    Args:
        payment_intent: Stripe PaymentIntent data from webhook
    """
    metadata = payment_intent.get("metadata", {})
    if not isinstance(metadata, dict):
        return

    order_id = metadata.get("order_id")
    if not order_id:
        pi_id = payment_intent.get("id")
        logger.warning("Payment succeeded but no order_id in metadata: %s", pi_id)
        return

    try:
        order = Order.objects.get(pk=int(order_id))
    except Order.DoesNotExist:
        logger.error("Order not found for payment_intent: order_id=%s", order_id)
        return
    except (ValueError, TypeError):
        logger.error("Invalid order_id in metadata: %s", order_id)
        return

    # Skip if already processed (idempotency)
    if order.status != OrderStatus.PENDING:
        logger.info(
            "Order already processed, skipping: order_id=%s status=%s",
            order_id,
            order.status,
        )
        return

    # Update order status
    now = datetime.now(UTC)
    estimated_ready = now + timedelta(minutes=30)  # Default 30 min estimate

    order.status = OrderStatus.CONFIRMED
    order.payment_status = PaymentStatus.CAPTURED
    order.confirmed_at = now
    order.estimated_ready_time = estimated_ready
    order.save(
        update_fields=[
            "status",
            "payment_status",
            "confirmed_at",
            "estimated_ready_time",
            "updated_at",
        ]
    )

    logger.info(
        "Order confirmed via webhook: order_id=%s confirmation_code=%s",
        order.pk,
        order.confirmation_code,
    )


def _handle_payment_failed(payment_intent: dict[str, object]) -> None:
    """
    Update order status when payment fails.

    Args:
        payment_intent: Stripe PaymentIntent data from webhook
    """
    metadata = payment_intent.get("metadata", {})
    if not isinstance(metadata, dict):
        return

    order_id = metadata.get("order_id")
    if not order_id:
        pi_id = payment_intent.get("id")
        logger.warning("Payment failed but no order_id in metadata: %s", pi_id)
        return

    try:
        order = Order.objects.get(pk=int(order_id))
    except Order.DoesNotExist:
        logger.error("Order not found for failed payment: order_id=%s", order_id)
        return
    except (ValueError, TypeError):
        logger.error("Invalid order_id in metadata: %s", order_id)
        return

    # Update payment status
    order.payment_status = PaymentStatus.FAILED
    order.save(update_fields=["payment_status", "updated_at"])

    logger.info(
        "Payment failed for order: order_id=%s confirmation_code=%s",
        order.pk,
        order.confirmation_code,
    )

    # Get failure reason
    last_error = payment_intent.get("last_payment_error")
    if isinstance(last_error, dict):
        error_message = last_error.get("message", "Unknown error")
        logger.info("Payment failure reason: %s", error_message)
