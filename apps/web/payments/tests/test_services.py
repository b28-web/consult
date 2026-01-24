"""Tests for payment services."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import stripe

from apps.web.payments.services import (
    PaymentError,
    cancel_payment_intent,
    create_payment_intent,
    create_refund,
    retrieve_payment_intent,
    verify_payment_intent,
)


class TestCreatePaymentIntent:
    """Tests for create_payment_intent."""

    @patch("apps.web.payments.services.stripe.PaymentIntent.create")
    def test_create_payment_intent_success(self, mock_create):
        """Test successful PaymentIntent creation."""
        mock_create.return_value = MagicMock(
            id="pi_test123",
            client_secret="pi_test123_secret_abc",
            amount=2500,
            currency="usd",
            status="requires_payment_method",
        )

        result = create_payment_intent(
            amount=Decimal("25.00"),
            metadata={"order_id": "123"},
        )

        mock_create.assert_called_once_with(
            amount=2500,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            metadata={"order_id": "123"},
        )
        assert result.id == "pi_test123"
        assert result.client_secret == "pi_test123_secret_abc"

    @patch("apps.web.payments.services.stripe.PaymentIntent.create")
    def test_create_payment_intent_with_custom_currency(self, mock_create):
        """Test PaymentIntent creation with custom currency."""
        mock_create.return_value = MagicMock(id="pi_test123")

        create_payment_intent(
            amount=Decimal("50.00"),
            currency="eur",
        )

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]["currency"] == "eur"
        assert call_args[1]["amount"] == 5000

    @patch("apps.web.payments.services.stripe.PaymentIntent.create")
    def test_create_payment_intent_rounds_amount(self, mock_create):
        """Test that amount is properly rounded to cents."""
        mock_create.return_value = MagicMock(id="pi_test123")

        create_payment_intent(amount=Decimal("12.995"))

        call_args = mock_create.call_args
        assert call_args[1]["amount"] == 1299

    @patch("apps.web.payments.services.stripe.PaymentIntent.create")
    def test_create_payment_intent_stripe_error(self, mock_create):
        """Test handling of Stripe API errors."""
        mock_create.side_effect = stripe.error.StripeError("Card declined")

        with pytest.raises(PaymentError) as exc_info:
            create_payment_intent(amount=Decimal("25.00"))

        assert "Card declined" in str(exc_info.value)


class TestRetrievePaymentIntent:
    """Tests for retrieve_payment_intent."""

    @patch("apps.web.payments.services.stripe.PaymentIntent.retrieve")
    def test_retrieve_payment_intent_success(self, mock_retrieve):
        """Test successful PaymentIntent retrieval."""
        mock_retrieve.return_value = MagicMock(
            id="pi_test123",
            status="succeeded",
        )

        result = retrieve_payment_intent("pi_test123")

        mock_retrieve.assert_called_once_with("pi_test123")
        assert result.status == "succeeded"

    @patch("apps.web.payments.services.stripe.PaymentIntent.retrieve")
    def test_retrieve_payment_intent_not_found(self, mock_retrieve):
        """Test handling of non-existent PaymentIntent."""
        mock_retrieve.side_effect = stripe.error.StripeError("No such payment_intent")

        with pytest.raises(PaymentError) as exc_info:
            retrieve_payment_intent("pi_invalid")

        assert "payment_intent" in str(exc_info.value)


class TestVerifyPaymentIntent:
    """Tests for verify_payment_intent."""

    @patch("apps.web.payments.services.retrieve_payment_intent")
    def test_verify_payment_intent_succeeded(self, mock_retrieve):
        """Test verification of succeeded payment."""
        mock_retrieve.return_value = MagicMock(status="succeeded")

        result = verify_payment_intent("pi_test123")

        assert result is True

    @patch("apps.web.payments.services.retrieve_payment_intent")
    def test_verify_payment_intent_not_succeeded(self, mock_retrieve):
        """Test verification of non-succeeded payment."""
        mock_retrieve.return_value = MagicMock(status="requires_payment_method")

        result = verify_payment_intent("pi_test123")

        assert result is False

    @patch("apps.web.payments.services.retrieve_payment_intent")
    def test_verify_payment_intent_error_returns_false(self, mock_retrieve):
        """Test that errors return False instead of raising."""
        mock_retrieve.side_effect = PaymentError("Not found")

        result = verify_payment_intent("pi_invalid")

        assert result is False


class TestCreateRefund:
    """Tests for create_refund."""

    @patch("apps.web.payments.services.stripe.Refund.create")
    def test_create_full_refund(self, mock_create):
        """Test creating a full refund."""
        mock_create.return_value = MagicMock(
            id="re_test123",
            amount=2500,
            status="succeeded",
        )

        result = create_refund("pi_test123")

        mock_create.assert_called_once_with(
            payment_intent="pi_test123",
            reason="requested_by_customer",
        )
        assert result.id == "re_test123"

    @patch("apps.web.payments.services.stripe.Refund.create")
    def test_create_partial_refund(self, mock_create):
        """Test creating a partial refund."""
        mock_create.return_value = MagicMock(id="re_test123")

        create_refund("pi_test123", amount_cents=1000)

        mock_create.assert_called_once_with(
            payment_intent="pi_test123",
            reason="requested_by_customer",
            amount=1000,
        )

    @patch("apps.web.payments.services.stripe.Refund.create")
    def test_create_refund_with_reason(self, mock_create):
        """Test creating a refund with custom reason."""
        mock_create.return_value = MagicMock(id="re_test123")

        create_refund("pi_test123", reason="duplicate")

        mock_create.assert_called_once_with(
            payment_intent="pi_test123",
            reason="duplicate",
        )

    @patch("apps.web.payments.services.stripe.Refund.create")
    def test_create_refund_stripe_error(self, mock_create):
        """Test handling of refund errors."""
        mock_create.side_effect = stripe.error.StripeError("Refund failed")

        with pytest.raises(PaymentError) as exc_info:
            create_refund("pi_test123")

        assert "Refund failed" in str(exc_info.value)


class TestCancelPaymentIntent:
    """Tests for cancel_payment_intent."""

    @patch("apps.web.payments.services.stripe.PaymentIntent.retrieve")
    def test_cancel_payment_intent_success(self, mock_retrieve):
        """Test successful cancellation."""
        mock_intent = MagicMock()
        mock_intent.cancel.return_value = MagicMock(
            id="pi_test123",
            status="canceled",
        )
        mock_retrieve.return_value = mock_intent

        result = cancel_payment_intent("pi_test123")

        mock_retrieve.assert_called_once_with("pi_test123")
        mock_intent.cancel.assert_called_once()
        assert result.status == "canceled"

    @patch("apps.web.payments.services.stripe.PaymentIntent.retrieve")
    def test_cancel_payment_intent_error(self, mock_retrieve):
        """Test handling of cancellation errors."""
        mock_retrieve.side_effect = stripe.error.StripeError("Cannot cancel")

        with pytest.raises(PaymentError) as exc_info:
            cancel_payment_intent("pi_test123")

        assert "Cannot cancel" in str(exc_info.value)
