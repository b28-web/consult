# 008-L: Order Submission to POS

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 4 (Online Ordering)

## Summary

After payment is confirmed, submit the order to the restaurant's POS system. This creates the order in Toast/Clover/Square so kitchen staff see it on their existing screens. Handle failures gracefully with retry logic and manual fallback.

## Acceptance Criteria

- [ ] `create_order()` method on POSAdapter protocol
- [ ] Toast order creation implementation
- [ ] Clover order creation implementation
- [ ] Square order creation implementation
- [ ] Async task triggered on payment success
- [ ] Map internal Order/OrderItem to POS order format
- [ ] Store POS order ID in Order.external_id
- [ ] Retry logic with exponential backoff (3 attempts)
- [ ] Failure notification to restaurant staff
- [ ] Manual retry endpoint for failed submissions
- [ ] Order status webhook updates from POS
- [ ] Saga pattern: Refund if POS submission fails permanently
- [ ] Integration tests with mock POS

## Implementation Notes

### Adapter Interface Extension

```python
# apps/web/pos/adapters/base.py

class POSAdapter(Protocol):
    # ... existing methods ...

    async def create_order(
        self,
        session: POSSession,
        location_id: str,
        order: POSOrder,
    ) -> POSOrderResult: ...

    async def get_order_status(
        self,
        session: POSSession,
        location_id: str,
        order_id: str,
    ) -> POSOrderStatus: ...


@dataclass
class POSOrder:
    """Order data to submit to POS."""
    external_reference: str      # Our order ID
    customer_name: str
    customer_email: str
    customer_phone: str
    order_type: str              # "pickup", "delivery"
    scheduled_time: datetime | None
    items: list[POSOrderItem]
    special_instructions: str
    subtotal: Decimal
    tax: Decimal
    tip: Decimal
    total: Decimal


@dataclass
class POSOrderItem:
    """Line item in POS order."""
    external_id: str             # MenuItem's POS ID
    name: str
    quantity: int
    unit_price: Decimal
    modifiers: list[POSOrderModifier]
    special_instructions: str


@dataclass
class POSOrderResult:
    """Result of order creation."""
    success: bool
    external_order_id: str | None
    error_message: str | None
    estimated_ready_time: datetime | None


@dataclass
class POSOrderStatus:
    """Current order status from POS."""
    status: str                  # "new", "in_progress", "ready", "completed"
    updated_at: datetime
    estimated_ready_time: datetime | None
```

### Toast Order Creation

```python
# apps/web/pos/adapters/toast.py

class ToastAdapter:
    # ... existing methods ...

    ORDERS_URL = f"{BASE_URL}/orders/v2/orders"

    async def create_order(
        self,
        session: POSSession,
        location_id: str,
        order: POSOrder,
    ) -> POSOrderResult:
        await self._rate_limiter.acquire()

        toast_order = {
            "entityType": "Order",
            "externalId": order.external_reference,
            "source": "Online",
            "restaurantGuid": location_id,
            "diningOption": {
                "guid": self._get_dining_option_guid(order.order_type),
            },
            "customer": {
                "firstName": order.customer_name.split()[0],
                "lastName": " ".join(order.customer_name.split()[1:]) or "Customer",
                "email": order.customer_email,
                "phone": order.customer_phone,
            },
            "promisedDate": order.scheduled_time.isoformat() if order.scheduled_time else None,
            "selections": [
                self._format_selection(item) for item in order.items
            ],
            "appliedServiceCharges": [],
            "appliedDiscounts": [],
        }

        try:
            response = await self._client.post(
                self.ORDERS_URL,
                headers={
                    "Authorization": f"Bearer {session.access_token}",
                    "Toast-Restaurant-External-ID": location_id,
                },
                json=toast_order,
            )
            response.raise_for_status()
            data = response.json()

            return POSOrderResult(
                success=True,
                external_order_id=data["guid"],
                error_message=None,
                estimated_ready_time=self._parse_ready_time(data),
            )

        except httpx.HTTPStatusError as e:
            return POSOrderResult(
                success=False,
                external_order_id=None,
                error_message=f"Toast API error: {e.response.status_code}",
                estimated_ready_time=None,
            )

    def _format_selection(self, item: POSOrderItem) -> dict:
        """Format order item for Toast API."""
        return {
            "itemGuid": item.external_id,
            "quantity": item.quantity,
            "modifiers": [
                {"modifierGuid": mod.external_id, "quantity": 1}
                for mod in item.modifiers
            ],
            "specialRequest": item.special_instructions,
        }
```

### Async Task

```python
# apps/web/pos/tasks.py

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.web.restaurant.models import Order
from apps.web.payments.services import create_refund
from .services import get_adapter_for_client, build_pos_order


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    retry_backoff=True,      # Exponential backoff
)
def submit_order_to_pos(self, order_id: str) -> None:
    """Submit confirmed order to POS system."""
    order = Order.objects.select_related("client").get(id=order_id)

    # Skip if already submitted
    if order.external_id:
        return

    # Skip if no POS configured
    profile = order.client.restaurant_profile
    if not profile or not profile.pos_provider:
        # Mark as manually handled
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return

    adapter = get_adapter_for_client(order.client)
    session = get_or_refresh_session(order.client)
    pos_order = build_pos_order(order)

    result = asyncio.run(
        adapter.create_order(session, profile.pos_location_id, pos_order)
    )

    if result.success:
        order.external_id = result.external_order_id
        order.status = "confirmed"
        if result.estimated_ready_time:
            # Could add estimated_ready_at field to Order
            pass
        order.save(update_fields=["external_id", "status"])

    else:
        # Retry or fail
        if self.request.retries < self.max_retries:
            raise self.retry(exc=Exception(result.error_message))
        else:
            # Max retries exceeded - handle failure
            handle_pos_submission_failure(order, result.error_message)


def handle_pos_submission_failure(order: Order, error: str) -> None:
    """Handle permanent POS submission failure."""
    with transaction.atomic():
        order.status = "pos_failed"
        order.save(update_fields=["status"])

        # Notify restaurant staff
        send_pos_failure_notification.delay(order.id, error)

        # Option 1: Refund automatically
        # create_refund(order.stripe_payment_intent_id)
        # order.payment_status = "refunded"

        # Option 2: Let staff handle manually (preferred)
        # Staff can retry via admin or process manually


def build_pos_order(order: Order) -> POSOrder:
    """Convert internal Order to POS format."""
    items = []
    for order_item in order.items.select_related("menu_item"):
        items.append(
            POSOrderItem(
                external_id=order_item.menu_item.external_id,
                name=order_item.menu_item.name,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                modifiers=[
                    POSOrderModifier(
                        external_id=Modifier.objects.get(id=mod_id).external_id,
                        name=Modifier.objects.get(id=mod_id).name,
                    )
                    for group in order_item.modifiers
                    for mod_id in group.get("selections", [])
                ],
                special_instructions=order_item.special_instructions,
            )
        )

    return POSOrder(
        external_reference=str(order.id),
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        order_type=order.order_type,
        scheduled_time=order.scheduled_time,
        items=items,
        special_instructions=order.special_instructions,
        subtotal=order.subtotal,
        tax=order.tax,
        tip=order.tip,
        total=order.total,
    )
```

### Manual Retry Endpoint

```python
# apps/web/restaurant/views.py

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retry_pos_submission(request, slug: str, order_id: str) -> Response:
    """Manually retry POS submission for a failed order."""
    order = get_object_or_404(Order, id=order_id, client__slug=slug)

    # Check permissions
    if request.user.client != order.client:
        raise PermissionDenied()

    if order.status != "pos_failed":
        return Response(
            {"error": "Order is not in failed state"},
            status=400,
        )

    # Reset status and retry
    order.status = "confirmed"
    order.save(update_fields=["status"])
    submit_order_to_pos.delay(str(order.id))

    return Response({"status": "retry_scheduled"})
```

### Order Status Webhook Handler

```python
# apps/web/pos/webhooks/handlers.py

def handle_order_status_change(client: Client, event: POSWebhookEvent) -> None:
    """Update order status when POS reports changes."""
    try:
        order = Order.objects.get(
            client=client,
            external_id=event.external_order_id,
        )

        status_map = {
            "in_progress": "preparing",
            "ready": "ready",
            "completed": "completed",
            "cancelled": "cancelled",
        }

        new_status = status_map.get(event.status)
        if new_status and order.status != new_status:
            order.status = new_status
            if new_status == "ready":
                order.ready_at = timezone.now()
            elif new_status == "completed":
                order.completed_at = timezone.now()
            order.save()

            # Notify customer
            if new_status == "ready":
                send_order_ready_notification.delay(order.id)

    except Order.DoesNotExist:
        pass  # Order created outside our system
```

### Saga Pattern for Refunds

If POS submission fails permanently, we need to refund the customer:

```python
# apps/web/pos/sagas.py

def compensate_failed_order(order: Order) -> None:
    """
    Compensation action when POS submission fails permanently.
    Called from handle_pos_submission_failure if auto-refund is enabled.
    """
    from apps.web.payments.services import create_refund

    if order.payment_status != "succeeded":
        return

    try:
        refund = create_refund(order.stripe_payment_intent_id)
        order.payment_status = "refunded"
        order.status = "cancelled"
        order.save(update_fields=["payment_status", "status"])

        # Notify customer
        send_order_cancelled_notification.delay(
            order.id,
            reason="We were unable to process your order with the restaurant. "
                   "A full refund has been issued.",
        )

    except stripe.error.StripeError as e:
        # Log for manual handling
        logger.error(f"Refund failed for order {order.id}: {e}")
```

### POS API Access Notes

**Toast:** Requires Partner API access for order creation. Standard API is read-only.

**Clover:** Order creation available with merchant authorization.

**Square:** Order creation available with ORDERS_WRITE scope.

## Testing

```python
# tests/pos/test_order_submission.py

class OrderSubmissionTests(TestCase):
    @patch("apps.web.pos.adapters.toast.ToastAdapter.create_order")
    def test_successful_submission(self, mock_create):
        mock_create.return_value = POSOrderResult(
            success=True,
            external_order_id="toast_123",
            error_message=None,
            estimated_ready_time=None,
        )

        order = OrderFactory(status="confirmed", external_id=None)
        submit_order_to_pos(str(order.id))

        order.refresh_from_db()
        self.assertEqual(order.external_id, "toast_123")

    @patch("apps.web.pos.adapters.toast.ToastAdapter.create_order")
    def test_failed_submission_retries(self, mock_create):
        mock_create.return_value = POSOrderResult(
            success=False,
            external_order_id=None,
            error_message="API error",
            estimated_ready_time=None,
        )

        order = OrderFactory(status="confirmed")

        with self.assertRaises(Retry):
            submit_order_to_pos(str(order.id))
```

## Dependencies

- 008-F, 008-G, 008-H (POS adapters with create_order method)
- 008-K (Stripe integration for refunds)
- 008-E (Webhook infrastructure for status updates)
- Celery for async task execution

## Progress

*To be updated during implementation*
