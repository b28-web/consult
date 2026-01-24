"""
Payment services - Stripe integration.

Stub implementation for 008-J. Full Stripe integration will be
implemented in ticket 008-K.
"""

import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class PaymentIntent:
    """Stripe PaymentIntent representation."""

    id: str
    client_secret: str
    amount: int  # In cents
    currency: str
    status: str


def create_payment_intent(
    amount: Decimal,
    currency: str = "usd",
    metadata: dict[str, Any] | None = None,  # noqa: ARG001 - used in full impl (008-K)
) -> PaymentIntent:
    """
    Create a Stripe PaymentIntent for the order.

    This is a stub implementation for 008-J.
    Full Stripe integration will be implemented in 008-K.

    Args:
        amount: Amount in dollars (will be converted to cents)
        currency: Currency code (default: USD)
        metadata: Additional metadata to attach to the payment

    Returns:
        PaymentIntent with client_secret for frontend
    """
    # TODO(008-K): Implement actual Stripe PaymentIntent creation
    # For now, return a mock PaymentIntent
    payment_intent_id = f"pi_mock_{secrets.token_hex(16)}"
    client_secret = f"{payment_intent_id}_secret_{secrets.token_hex(8)}"

    return PaymentIntent(
        id=payment_intent_id,
        client_secret=client_secret,
        amount=int(amount * 100),  # Convert to cents
        currency=currency,
        status="requires_payment_method",
    )


def verify_payment_intent(payment_intent_id: str) -> bool:
    """
    Verify that a PaymentIntent has been successfully paid.

    This is a stub implementation for 008-J.
    Full Stripe integration will be implemented in 008-K.

    Args:
        payment_intent_id: The Stripe PaymentIntent ID

    Returns:
        True if payment succeeded, False otherwise
    """
    # TODO(008-K): Implement actual Stripe PaymentIntent verification
    # For now, accept all mock payment intents
    return payment_intent_id.startswith("pi_")
