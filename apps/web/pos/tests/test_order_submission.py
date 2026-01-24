"""Tests for POS order submission service."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.web.pos.services import (
    OrderSubmissionError,
    build_pos_order,
    compensate_failed_order,
    handle_pos_submission_failure,
    submit_order_to_pos,
)
from apps.web.pos.tasks import retry_failed_order, submit_order_to_pos_task
from apps.web.restaurant.models import OrderStatus, PaymentStatus
from apps.web.restaurant.tests.factories import (
    ClientFactory,
    MenuItemFactory,
    OrderFactory,
    OrderItemFactory,
    RestaurantProfileFactory,
)


@pytest.fixture
def client():
    """Create a test client."""
    return ClientFactory()


@pytest.fixture
def restaurant_profile(client):
    """Create a restaurant profile with mock POS."""
    return RestaurantProfileFactory(
        client=client,
        pos_provider="toast",
        pos_location_id="test-location-123",
    )


@pytest.fixture
def menu_item(client):
    """Create a menu item."""
    return MenuItemFactory(
        client=client,
        external_id="item-ext-123",
        name="Test Burger",
        price=Decimal("12.99"),
    )


@pytest.fixture
def order(client, menu_item):
    """Create a test order."""
    order = OrderFactory(
        client=client,
        status=OrderStatus.CONFIRMED,
        payment_status=PaymentStatus.CAPTURED,
        stripe_payment_intent_id="pi_test_123",
    )
    OrderItemFactory(
        client=client,
        order=order,
        menu_item=menu_item,
        item_name=menu_item.name,
        unit_price=menu_item.price,
        line_total=menu_item.price,
    )
    return order


@pytest.mark.django_db
class TestBuildPOSOrder:
    """Tests for build_pos_order function."""

    def test_builds_order_from_model(self, order):
        """Test converting Django Order to POSOrder."""
        pos_order = build_pos_order(order)

        assert pos_order.customer_name == order.customer_name
        assert pos_order.customer_email == order.customer_email
        assert pos_order.subtotal == order.subtotal
        assert pos_order.total == order.total
        assert len(pos_order.items) == 1

    def test_includes_item_details(self, order):
        """Test that order items are correctly mapped."""
        pos_order = build_pos_order(order)

        item = pos_order.items[0]
        order_item = order.items.first()

        assert item.name == order_item.item_name
        assert item.quantity == order_item.quantity
        assert item.unit_price == order_item.unit_price


@pytest.mark.django_db
class TestSubmitOrderToPOS:
    """Tests for submit_order_to_pos function."""

    def test_skips_already_submitted_order(self, order):
        """Test that already submitted orders are skipped."""
        order.external_id = "pos-order-existing"
        order.save()

        result = submit_order_to_pos(order.pk)

        assert result["external_id"] == "pos-order-existing"

    def test_skips_order_with_wrong_status(self, order):
        """Test that orders not ready for submission raise error."""
        order.status = OrderStatus.COMPLETED
        order.save()

        with pytest.raises(OrderSubmissionError) as exc_info:
            submit_order_to_pos(order.pk)

        assert "not ready for submission" in str(exc_info.value)
        assert exc_info.value.is_retryable is False

    def test_handles_missing_order(self):
        """Test that missing order raises error."""
        with pytest.raises(OrderSubmissionError) as exc_info:
            submit_order_to_pos(99999)

        assert "not found" in str(exc_info.value)
        assert exc_info.value.is_retryable is False

    def test_handles_no_restaurant_profile(self, order):
        """Test order without POS configured is marked confirmed."""
        result = submit_order_to_pos(order.pk)

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
        assert result["external_id"] is None

    def test_handles_no_pos_provider(self, order, restaurant_profile):
        """Test order with profile but no POS is marked confirmed."""
        restaurant_profile.pos_provider = ""
        restaurant_profile.save()

        result = submit_order_to_pos(order.pk)

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
        assert result["external_id"] is None

    def test_successful_submission(self, order, restaurant_profile):
        """Test successful POS submission updates order."""
        result = submit_order_to_pos(order.pk)

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
        assert order.external_id is not None
        assert order.submitted_at is not None
        assert result["external_id"] == order.external_id


@pytest.mark.django_db
class TestSubmitOrderToPOSTask:
    """Tests for the task wrapper."""

    def test_task_returns_success_on_completion(self, order, restaurant_profile):
        """Test task returns success dict."""
        result = submit_order_to_pos_task(order.pk)

        assert result["success"] is True
        assert result["order_id"] == order.pk
        assert result["external_id"] is not None

    def test_task_handles_retryable_error(self, order, restaurant_profile):
        """Test task handles retryable errors correctly."""
        with patch(
            "apps.web.pos.services.order_submission._submit_order_async"
        ) as mock_submit:
            from apps.web.pos.exceptions import POSAPIError

            mock_submit.side_effect = POSAPIError("API error", provider="toast")

            result = submit_order_to_pos_task(order.pk, retry_count=0)

            assert result["success"] is False
            assert result["is_retryable"] is True
            assert result["retry_count"] == 0

    def test_task_handles_permanent_failure(self, order, restaurant_profile):
        """Test task handles permanent failure after max retries."""
        with patch(
            "apps.web.pos.services.order_submission._submit_order_async"
        ) as mock_submit:
            from apps.web.pos.exceptions import POSAPIError

            mock_submit.side_effect = POSAPIError("API error", provider="toast")

            result = submit_order_to_pos_task(order.pk, retry_count=3)

            assert result["success"] is False
            assert result["is_retryable"] is False
            assert result["status"] == "pos_failed"

            order.refresh_from_db()
            assert order.status == "pos_failed"


@pytest.mark.django_db
class TestRetryFailedOrder:
    """Tests for retry_failed_order function."""

    def test_rejects_non_failed_order(self, order, restaurant_profile):
        """Test that non-failed orders cannot be retried."""
        result = retry_failed_order(order.pk)

        assert result["success"] is False
        assert "not in pos_failed state" in result["error"]

    def test_retries_failed_order(self, order, restaurant_profile):
        """Test that failed orders can be retried."""
        order.status = "pos_failed"
        order.save()

        result = retry_failed_order(order.pk)

        assert result["success"] is True
        order.refresh_from_db()
        assert order.external_id is not None


@pytest.mark.django_db
class TestHandlePOSSubmissionFailure:
    """Tests for handle_pos_submission_failure function."""

    def test_marks_order_as_failed(self, order):
        """Test that order status is updated to pos_failed."""
        handle_pos_submission_failure(order.pk, "Test error")

        order.refresh_from_db()
        assert order.status == "pos_failed"

    def test_handles_missing_order(self):
        """Test that missing order is handled gracefully."""
        # Should not raise
        handle_pos_submission_failure(99999, "Test error")


@pytest.mark.django_db
class TestCompensateFailedOrder:
    """Tests for compensate_failed_order (saga pattern)."""

    def test_skips_unpaid_order(self, order):
        """Test that unpaid orders are not refunded."""
        order.payment_status = PaymentStatus.PENDING
        order.save()

        result = compensate_failed_order(order)

        assert result is False

    def test_skips_order_without_payment_intent(self, order):
        """Test that orders without payment intent are not refunded."""
        order.payment_status = PaymentStatus.CAPTURED
        order.stripe_payment_intent_id = ""
        order.save()

        result = compensate_failed_order(order)

        assert result is False

    @patch("apps.web.pos.services.order_submission.create_refund")
    def test_refunds_and_cancels_order(self, mock_refund, order):
        """Test successful refund updates order status."""
        order.payment_status = PaymentStatus.CAPTURED
        order.stripe_payment_intent_id = "pi_test_123"
        order.save()

        result = compensate_failed_order(order)

        assert result is True
        mock_refund.assert_called_once_with("pi_test_123")

        order.refresh_from_db()
        assert order.payment_status == PaymentStatus.REFUNDED
        assert order.status == OrderStatus.CANCELLED

    @patch("apps.web.pos.services.order_submission.create_refund")
    def test_handles_refund_failure(self, mock_refund, order):
        """Test refund failure is handled gracefully."""
        from apps.web.payments.services import PaymentError

        mock_refund.side_effect = PaymentError("Refund failed")

        order.payment_status = PaymentStatus.CAPTURED
        order.stripe_payment_intent_id = "pi_test_123"
        order.save()

        result = compensate_failed_order(order)

        assert result is False
        # Order status should not change on refund failure
        order.refresh_from_db()
        assert order.payment_status == PaymentStatus.CAPTURED
