"""
Payment services - Stripe integration.

Provides functions for creating and managing Stripe PaymentIntents.
"""

from decimal import Decimal
from typing import Any

from django.conf import settings

import stripe

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentError(Exception):
    """Error during payment processing."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def create_payment_intent(
    amount: Decimal,
    currency: str = "usd",
    metadata: dict[str, Any] | None = None,
) -> stripe.PaymentIntent:
    """
    Create a Stripe PaymentIntent for the order.

    Args:
        amount: Amount in dollars (will be converted to cents)
        currency: Currency code (default: USD)
        metadata: Additional metadata to attach to the payment (e.g., order_id)

    Returns:
        stripe.PaymentIntent with client_secret for frontend

    Raises:
        PaymentError: If Stripe API call fails
    """
    amount_cents = int(amount * 100)

    try:
        return stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            automatic_payment_methods={"enabled": True},
            metadata=metadata or {},
        )
    except stripe.error.StripeError as e:
        raise PaymentError(
            message=str(e.user_message or e),
            code=getattr(e, "code", None),
        ) from e


def retrieve_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
    """
    Retrieve a PaymentIntent from Stripe.

    Args:
        payment_intent_id: The Stripe PaymentIntent ID (pi_xxx)

    Returns:
        stripe.PaymentIntent with current status

    Raises:
        PaymentError: If PaymentIntent not found or API call fails
    """
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        raise PaymentError(
            message=str(e.user_message or e),
            code=getattr(e, "code", None),
        ) from e


def verify_payment_intent(payment_intent_id: str) -> bool:
    """
    Verify that a PaymentIntent has been successfully paid.

    Args:
        payment_intent_id: The Stripe PaymentIntent ID

    Returns:
        True if payment succeeded, False otherwise
    """
    try:
        intent = retrieve_payment_intent(payment_intent_id)
        return bool(intent.status == "succeeded")
    except PaymentError:
        return False


def create_refund(
    payment_intent_id: str,
    amount_cents: int | None = None,
    reason: str = "requested_by_customer",
) -> stripe.Refund:
    """
    Create a refund for a payment.

    Args:
        payment_intent_id: The Stripe PaymentIntent ID to refund
        amount_cents: Amount to refund in cents (None = full refund)
        reason: Reason for refund - one of:
            - "duplicate"
            - "fraudulent"
            - "requested_by_customer"

    Returns:
        stripe.Refund object

    Raises:
        PaymentError: If refund fails
    """
    try:
        params: dict[str, Any] = {
            "payment_intent": payment_intent_id,
            "reason": reason,
        }
        if amount_cents is not None:
            params["amount"] = amount_cents

        return stripe.Refund.create(**params)
    except stripe.error.StripeError as e:
        raise PaymentError(
            message=str(e.user_message or e),
            code=getattr(e, "code", None),
        ) from e


def cancel_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
    """
    Cancel a PaymentIntent that has not yet been captured.

    Args:
        payment_intent_id: The Stripe PaymentIntent ID to cancel

    Returns:
        Cancelled stripe.PaymentIntent

    Raises:
        PaymentError: If cancellation fails
    """
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        result: stripe.PaymentIntent = intent.cancel()
        return result
    except stripe.error.StripeError as e:
        raise PaymentError(
            message=str(e.user_message or e),
            code=getattr(e, "code", None),
        ) from e
