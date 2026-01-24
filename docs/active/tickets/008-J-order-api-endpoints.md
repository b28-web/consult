# 008-J: Order API Endpoints

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 4 (Online Ordering)

## Summary

Create REST API endpoints for order creation, retrieval, and status updates. These endpoints handle the server-side order flow: validate cart, calculate totals, create Stripe PaymentIntent, and store the order.

## Acceptance Criteria

- [ ] `POST /api/clients/{slug}/orders` - Create new order
- [ ] `GET /api/clients/{slug}/orders/{id}` - Get order details
- [ ] `POST /api/clients/{slug}/orders/{id}/confirm` - Confirm order after payment
- [ ] `GET /api/clients/{slug}/orders/{id}/status` - Poll order status
- [ ] Request validation (items exist, available, prices match)
- [ ] Tax calculation
- [ ] Tip handling
- [ ] Stripe PaymentIntent creation (see 008-K)
- [ ] Order stored in pending state until payment confirmed
- [ ] Idempotency key support to prevent duplicate orders
- [ ] Rate limiting on order creation
- [ ] Error responses for validation failures
- [ ] Integration tests

## Implementation Notes

### Endpoints

#### Create Order

```
POST /api/clients/{slug}/orders
Content-Type: application/json
Idempotency-Key: {uuid}

{
  "customer": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+15555555555"
  },
  "order_type": "pickup",
  "scheduled_time": "2026-01-21T18:30:00Z",  // optional
  "items": [
    {
      "menu_item_id": 123,
      "quantity": 2,
      "modifiers": [
        {
          "group_id": 10,
          "selections": [5, 6]  // modifier IDs
        }
      ],
      "special_instructions": "No onions"
    }
  ],
  "special_instructions": "Ring doorbell",
  "tip": 5.00
}

Response 201:
{
  "order_id": "ord_abc123",
  "status": "pending_payment",
  "subtotal": 45.00,
  "tax": 3.60,
  "tip": 5.00,
  "total": 53.60,
  "stripe_client_secret": "pi_xxx_secret_yyy",
  "created_at": "2026-01-21T12:00:00Z"
}

Response 400 (validation error):
{
  "error": "validation_error",
  "details": [
    {"field": "items[0].menu_item_id", "message": "Item not found"},
    {"field": "items[1].menu_item_id", "message": "Item currently unavailable (86'd)"}
  ]
}
```

#### Get Order

```
GET /api/clients/{slug}/orders/{order_id}

Response 200:
{
  "order_id": "ord_abc123",
  "status": "confirmed",
  "customer": {...},
  "items": [...],
  "subtotal": 45.00,
  "tax": 3.60,
  "tip": 5.00,
  "total": 53.60,
  "order_type": "pickup",
  "scheduled_time": "2026-01-21T18:30:00Z",
  "created_at": "...",
  "confirmed_at": "...",
  "estimated_ready_at": "..."
}
```

#### Confirm Order

Called after Stripe payment succeeds (or from Stripe webhook):

```
POST /api/clients/{slug}/orders/{order_id}/confirm
{
  "payment_intent_id": "pi_xxx"
}

Response 200:
{
  "order_id": "ord_abc123",
  "status": "confirmed",
  "estimated_ready_at": "2026-01-21T18:45:00Z"
}
```

#### Poll Status

```
GET /api/clients/{slug}/orders/{order_id}/status

Response 200:
{
  "status": "preparing",
  "updated_at": "2026-01-21T18:35:00Z",
  "estimated_ready_at": "2026-01-21T18:45:00Z"
}
```

### Implementation

```python
# apps/web/restaurant/views.py

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction

from .models import Order, OrderItem, MenuItem
from .serializers import OrderCreateSerializer, OrderSerializer
from apps.web.payments.services import create_payment_intent


@api_view(["POST"])
@idempotency_key_required
def create_order(request, slug: str) -> Response:
    """Create a new order and return Stripe client secret."""
    client = get_object_or_404(Client, slug=slug)

    serializer = OrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Validate all items exist and are available
    errors = validate_order_items(client, data["items"])
    if errors:
        return Response(
            {"error": "validation_error", "details": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        # Calculate totals
        subtotal = calculate_subtotal(client, data["items"])
        tax = calculate_tax(subtotal, client)
        tip = data.get("tip", 0)
        total = subtotal + tax + tip

        # Create order record
        order = Order.objects.create(
            client=client,
            customer_name=data["customer"]["name"],
            customer_email=data["customer"]["email"],
            customer_phone=data["customer"].get("phone", ""),
            order_type=data["order_type"],
            scheduled_time=data.get("scheduled_time"),
            special_instructions=data.get("special_instructions", ""),
            subtotal=subtotal,
            tax=tax,
            tip=tip,
            total=total,
            status="pending_payment",
        )

        # Create order items
        for item_data in data["items"]:
            menu_item = MenuItem.objects.get(
                client=client, id=item_data["menu_item_id"]
            )
            OrderItem.objects.create(
                order=order,
                client=client,
                menu_item=menu_item,
                quantity=item_data["quantity"],
                unit_price=calculate_item_price(menu_item, item_data["modifiers"]),
                modifiers=item_data["modifiers"],
                special_instructions=item_data.get("special_instructions", ""),
            )

        # Create Stripe PaymentIntent
        payment_intent = create_payment_intent(
            amount_cents=int(total * 100),
            currency="usd",
            metadata={
                "order_id": str(order.id),
                "client_slug": slug,
            },
        )
        order.stripe_payment_intent_id = payment_intent.id
        order.save(update_fields=["stripe_payment_intent_id"])

    return Response(
        {
            "order_id": str(order.id),
            "status": order.status,
            "subtotal": float(order.subtotal),
            "tax": float(order.tax),
            "tip": float(order.tip),
            "total": float(order.total),
            "stripe_client_secret": payment_intent.client_secret,
            "created_at": order.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


def validate_order_items(client: Client, items: list) -> list[dict]:
    """Validate all items exist and are available."""
    errors = []
    for i, item_data in enumerate(items):
        try:
            menu_item = MenuItem.objects.get(
                client=client, id=item_data["menu_item_id"]
            )
            if not menu_item.is_available:
                errors.append({
                    "field": f"items[{i}].menu_item_id",
                    "message": f"'{menu_item.name}' is currently unavailable",
                })
        except MenuItem.DoesNotExist:
            errors.append({
                "field": f"items[{i}].menu_item_id",
                "message": "Item not found",
            })
    return errors


def calculate_subtotal(client: Client, items: list) -> Decimal:
    """Calculate order subtotal including modifier prices."""
    total = Decimal("0")
    for item_data in items:
        menu_item = MenuItem.objects.get(
            client=client, id=item_data["menu_item_id"]
        )
        item_price = calculate_item_price(menu_item, item_data["modifiers"])
        total += item_price * item_data["quantity"]
    return total


def calculate_item_price(menu_item: MenuItem, modifiers: list) -> Decimal:
    """Calculate item price with modifier adjustments."""
    price = menu_item.price
    for mod_group in modifiers:
        for mod_id in mod_group["selections"]:
            modifier = Modifier.objects.get(id=mod_id)
            price += modifier.price_adjustment
    return price


def calculate_tax(subtotal: Decimal, client: Client) -> Decimal:
    """Calculate tax based on client location."""
    # TODO: Use proper tax calculation (Stripe Tax or POS)
    # For now, use a fixed rate
    tax_rate = Decimal("0.08")  # 8%
    return (subtotal * tax_rate).quantize(Decimal("0.01"))
```

### Idempotency

```python
# apps/web/core/decorators.py

from functools import wraps
from django.core.cache import cache

def idempotency_key_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return Response(
                {"error": "Idempotency-Key header required"},
                status=400,
            )

        cache_key = f"idempotency:{key}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached["data"], status=cached["status"])

        response = view_func(request, *args, **kwargs)

        # Cache successful responses for 24 hours
        if response.status_code < 400:
            cache.set(
                cache_key,
                {"data": response.data, "status": response.status_code},
                timeout=86400,
            )

        return response
    return wrapper
```

### URL Configuration

```python
# apps/web/restaurant/urls.py

urlpatterns = [
    path("menu", views.menu_list, name="menu-list"),
    path("menu/<int:menu_id>", views.menu_detail, name="menu-detail"),
    path("availability", views.availability, name="availability"),
    path("orders", views.create_order, name="order-create"),
    path("orders/<uuid:order_id>", views.get_order, name="order-detail"),
    path("orders/<uuid:order_id>/confirm", views.confirm_order, name="order-confirm"),
    path("orders/<uuid:order_id>/status", views.order_status, name="order-status"),
]
```

## Dependencies

- 008-B (Order and OrderItem models)
- 008-K (Stripe PaymentIntent creation)

## Progress

### 2026-01-24
- **Completed** all acceptance criteria
- Added Pydantic schemas for order requests and responses in `apps/web/restaurant/serializers.py`
- Created idempotency key decorator in `apps/web/core/decorators.py`
- Implemented order API views in `apps/web/restaurant/views.py`:
  - `POST /api/clients/{slug}/orders` - Create order with validation, pricing, PaymentIntent
  - `GET /api/clients/{slug}/orders/{order_id}` - Get order details
  - `POST /api/clients/{slug}/orders/{order_id}/confirm` - Confirm after payment
  - `GET /api/clients/{slug}/orders/{order_id}/status` - Poll order status
- Created stub payments module in `apps/web/payments/` (full Stripe impl in 008-K)
- Added URL routes in `apps/web/restaurant/urls.py`
- Wrote 18 integration tests, all passing
- Features implemented:
  - Item validation (exists, available, from active menu)
  - Modifier validation (required groups, selection counts)
  - Price calculation with modifiers
  - Tax calculation using RestaurantProfile.tax_rate
  - Delivery fee calculation for delivery orders
  - Idempotency key support for duplicate prevention
  - CORS headers for Astro frontend access
  - Multi-tenant isolation verified
