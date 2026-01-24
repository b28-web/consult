"""Tests for Stripe webhook handlers."""

import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

import stripe

from apps.web.restaurant.models import OrderStatus, PaymentStatus
from apps.web.restaurant.tests.factories import ClientFactory, OrderFactory


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test123")
class TestStripeWebhook(TestCase):
    """Tests for the Stripe webhook endpoint."""

    def setUp(self):
        self.http_client = Client()
        self.url = "/payments/webhooks/stripe"
        self.restaurant_client = ClientFactory()

    def _make_webhook_request(
        self, event_type: str, data: dict, signature: str = "valid"
    ):
        """Helper to make webhook requests."""
        payload = json.dumps(
            {
                "type": event_type,
                "data": {"object": data},
            }
        )

        return self.http_client.post(
            self.url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature,
        )

    @patch("stripe.Webhook.construct_event")
    def test_payment_succeeded_updates_order(self, mock_construct):
        """Test that payment_intent.succeeded updates order status."""
        order = OrderFactory(
            client=self.restaurant_client,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
        )

        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {"order_id": str(order.pk)},
                }
            },
        }

        response = self._make_webhook_request(
            "payment_intent.succeeded",
            {"id": "pi_test123", "metadata": {"order_id": str(order.pk)}},
        )

        assert response.status_code == 200

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
        assert order.payment_status == PaymentStatus.CAPTURED
        assert order.confirmed_at is not None
        assert order.estimated_ready_time is not None

    @patch("stripe.Webhook.construct_event")
    def test_payment_succeeded_idempotent(self, mock_construct):
        """Test that processing same webhook twice is idempotent."""
        order = OrderFactory(
            client=self.restaurant_client,
            status=OrderStatus.CONFIRMED,  # Already processed
            payment_status=PaymentStatus.CAPTURED,
        )

        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {"order_id": str(order.pk)},
                }
            },
        }

        response = self._make_webhook_request(
            "payment_intent.succeeded",
            {"id": "pi_test123", "metadata": {"order_id": str(order.pk)}},
        )

        assert response.status_code == 200
        # Order should remain unchanged
        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED

    @patch("stripe.Webhook.construct_event")
    def test_payment_failed_updates_order(self, mock_construct):
        """Test that payment_intent.payment_failed updates payment status."""
        order = OrderFactory(
            client=self.restaurant_client,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
        )

        mock_construct.return_value = {
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {"order_id": str(order.pk)},
                    "last_payment_error": {"message": "Card declined"},
                }
            },
        }

        response = self._make_webhook_request(
            "payment_intent.payment_failed",
            {
                "id": "pi_test123",
                "metadata": {"order_id": str(order.pk)},
                "last_payment_error": {"message": "Card declined"},
            },
        )

        assert response.status_code == 200

        order.refresh_from_db()
        assert order.payment_status == PaymentStatus.FAILED
        assert order.status == OrderStatus.PENDING  # Order status unchanged

    @patch("stripe.Webhook.construct_event")
    def test_missing_order_id_in_metadata(self, mock_construct):
        """Test handling of webhook without order_id in metadata."""
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {},  # No order_id
                }
            },
        }

        response = self._make_webhook_request(
            "payment_intent.succeeded",
            {"id": "pi_test123", "metadata": {}},
        )

        # Should return 200 (webhook processed, just not acted upon)
        assert response.status_code == 200

    @patch("stripe.Webhook.construct_event")
    def test_nonexistent_order_id(self, mock_construct):
        """Test handling of webhook with non-existent order ID."""
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {"order_id": "999999"},
                }
            },
        }

        response = self._make_webhook_request(
            "payment_intent.succeeded",
            {"id": "pi_test123", "metadata": {"order_id": "999999"}},
        )

        # Should return 200 (don't retry for non-existent orders)
        assert response.status_code == 200

    @patch("stripe.Webhook.construct_event")
    def test_unhandled_event_type(self, mock_construct):
        """Test that unhandled event types return 200."""
        mock_construct.return_value = {
            "type": "customer.created",
            "data": {"object": {"id": "cus_test123"}},
        }

        response = self._make_webhook_request(
            "customer.created",
            {"id": "cus_test123"},
        )

        assert response.status_code == 200

    def test_invalid_payload_returns_400(self):
        """Test that invalid JSON returns 400."""
        response = self.http_client.post(
            self.url,
            data="not valid json",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        assert response.status_code == 400

    @patch("stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct):
        """Test that invalid signature returns 400."""
        mock_construct.side_effect = stripe.SignatureVerificationError(
            "Invalid signature", "sig"
        )

        response = self._make_webhook_request(
            "payment_intent.succeeded",
            {"id": "pi_test123"},
            signature="invalid_signature",
        )

        assert response.status_code == 400
