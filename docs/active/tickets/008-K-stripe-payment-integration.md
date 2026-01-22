# 008-K: Stripe Payment Integration

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 4 (Online Ordering)

## Summary

Integrate Stripe for payment processing in the online ordering flow. This includes creating PaymentIntents on the backend, embedding Stripe Elements on the frontend, and handling payment confirmation via webhooks.

## Acceptance Criteria

- [ ] Stripe Python SDK installed and configured
- [ ] `create_payment_intent()` service function
- [ ] Stripe client secret returned in order creation response
- [ ] Stripe Elements embedded on checkout page
- [ ] Payment form with card input
- [ ] Client-side payment confirmation
- [ ] Stripe webhook handler for `payment_intent.succeeded`
- [ ] Stripe webhook handler for `payment_intent.payment_failed`
- [ ] Order status updated on payment events
- [ ] Webhook signature verification
- [ ] Refund support (for cancelled orders)
- [ ] Test mode support for development
- [ ] Unit tests with Stripe mocks
- [ ] Integration tests with Stripe test mode

## Implementation Notes

### Backend: Payment Service

```python
# apps/web/payments/__init__.py
# apps/web/payments/services.py

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(
    amount_cents: int,
    currency: str = "usd",
    metadata: dict | None = None,
) -> stripe.PaymentIntent:
    """Create a Stripe PaymentIntent for the order."""
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        automatic_payment_methods={"enabled": True},
        metadata=metadata or {},
    )


def confirm_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
    """Retrieve and verify payment intent status."""
    return stripe.PaymentIntent.retrieve(payment_intent_id)


def create_refund(
    payment_intent_id: str,
    amount_cents: int | None = None,
    reason: str = "requested_by_customer",
) -> stripe.Refund:
    """Create a refund for a payment."""
    params = {
        "payment_intent": payment_intent_id,
        "reason": reason,
    }
    if amount_cents:
        params["amount"] = amount_cents
    return stripe.Refund.create(**params)
```

### Backend: Webhook Handler

```python
# apps/web/payments/webhooks.py

import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from apps.web.restaurant.models import Order


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    # Handle the event
    match event["type"]:
        case "payment_intent.succeeded":
            handle_payment_succeeded(event["data"]["object"])
        case "payment_intent.payment_failed":
            handle_payment_failed(event["data"]["object"])
        case _:
            pass  # Ignore other events

    return HttpResponse(status=200)


def handle_payment_succeeded(payment_intent: dict) -> None:
    """Update order status when payment succeeds."""
    order_id = payment_intent.get("metadata", {}).get("order_id")
    if not order_id:
        return

    try:
        order = Order.objects.get(id=order_id)
        if order.status == "pending_payment":
            order.status = "confirmed"
            order.payment_status = "succeeded"
            order.confirmed_at = timezone.now()
            order.save(update_fields=["status", "payment_status", "confirmed_at"])

            # Trigger POS order submission (see 008-L)
            submit_order_to_pos.delay(order.id)

            # Send confirmation email
            send_order_confirmation.delay(order.id)

    except Order.DoesNotExist:
        pass


def handle_payment_failed(payment_intent: dict) -> None:
    """Update order status when payment fails."""
    order_id = payment_intent.get("metadata", {}).get("order_id")
    if not order_id:
        return

    try:
        order = Order.objects.get(id=order_id)
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])
    except Order.DoesNotExist:
        pass
```

### Backend: URL Configuration

```python
# apps/web/payments/urls.py

from django.urls import path
from . import webhooks

urlpatterns = [
    path("webhooks/stripe", webhooks.stripe_webhook, name="stripe-webhook"),
]

# Add to main urls.py
path("payments/", include("payments.urls")),
```

### Frontend: Stripe Elements

```astro
<!-- sites/_template-restaurant/src/components/checkout/PaymentForm.astro -->
---
interface Props {
  clientSecret: string;
}
const { clientSecret } = Astro.props;
---

<div id="payment-form">
  <div id="payment-element">
    <!-- Stripe Elements will be inserted here -->
  </div>
  <div id="payment-errors" class="text-red-500 text-sm mt-2"></div>
</div>

<script define:vars={{ clientSecret }}>
  import { loadStripe } from "@stripe/stripe-js";

  const stripePublicKey = import.meta.env.PUBLIC_STRIPE_KEY;

  async function initializePayment() {
    const stripe = await loadStripe(stripePublicKey);
    const elements = stripe.elements({
      clientSecret,
      appearance: {
        theme: "stripe",
        variables: {
          colorPrimary: "#0066cc",
        },
      },
    });

    const paymentElement = elements.create("payment");
    paymentElement.mount("#payment-element");

    // Store for form submission
    window.stripeElements = { stripe, elements };
  }

  initializePayment();
</script>
```

### Frontend: Checkout Submission

```typescript
// sites/_template-restaurant/src/lib/checkout.ts

import type { Stripe, StripeElements } from "@stripe/stripe-js";

interface CheckoutResult {
  success: boolean;
  orderId?: string;
  error?: string;
}

export async function submitOrder(
  customerData: CustomerData,
  cartState: CartState,
): Promise<CheckoutResult> {
  // 1. Create order on backend
  const orderResponse = await fetch(`/api/clients/${clientSlug}/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({
      customer: customerData,
      order_type: cartState.orderType,
      scheduled_time: cartState.scheduledTime,
      items: cartState.items.map((item) => ({
        menu_item_id: item.menuItemId,
        quantity: item.quantity,
        modifiers: item.modifiers.map((m) => ({
          group_id: m.groupId,
          selections: m.selections.map((s) => s.id),
        })),
        special_instructions: item.specialInstructions,
      })),
      special_instructions: cartState.specialInstructions,
      tip: cartState.tip,
    }),
  });

  if (!orderResponse.ok) {
    const error = await orderResponse.json();
    return { success: false, error: error.details?.[0]?.message || "Order failed" };
  }

  const order = await orderResponse.json();

  // 2. Confirm payment with Stripe
  const { stripe, elements } = window.stripeElements as {
    stripe: Stripe;
    elements: StripeElements;
  };

  const { error: stripeError } = await stripe.confirmPayment({
    elements,
    confirmParams: {
      return_url: `${window.location.origin}/order-confirmation?order_id=${order.order_id}`,
    },
  });

  if (stripeError) {
    return { success: false, error: stripeError.message };
  }

  // If we get here, payment is processing (redirect will happen)
  return { success: true, orderId: order.order_id };
}
```

### Frontend: Order Confirmation Page

```astro
<!-- sites/_template-restaurant/src/pages/order-confirmation.astro -->
---
import RestaurantLayout from "../layouts/RestaurantLayout.astro";
---

<RestaurantLayout title="Order Confirmed">
  <div class="container mx-auto px-4 py-16 text-center">
    <div id="loading" class="animate-pulse">
      <p>Confirming your order...</p>
    </div>

    <div id="success" class="hidden">
      <div class="text-green-500 text-6xl mb-4">✓</div>
      <h1 class="text-2xl font-bold mb-2">Order Confirmed!</h1>
      <p class="text-gray-600 mb-4">Order #<span id="order-number"></span></p>
      <p>We've sent a confirmation email to <span id="customer-email"></span></p>
      <div id="pickup-info" class="mt-6 p-4 bg-gray-100 rounded-lg">
        <p class="font-semibold">Estimated Ready Time</p>
        <p id="ready-time" class="text-xl"></p>
      </div>
    </div>

    <div id="error" class="hidden">
      <div class="text-red-500 text-6xl mb-4">✗</div>
      <h1 class="text-2xl font-bold mb-2">Payment Failed</h1>
      <p id="error-message" class="text-gray-600"></p>
      <a href="/checkout" class="btn btn-primary mt-4">Try Again</a>
    </div>
  </div>
</RestaurantLayout>

<script>
  // Check payment status on load
  const params = new URLSearchParams(window.location.search);
  const orderId = params.get("order_id");
  const paymentIntent = params.get("payment_intent");

  async function checkStatus() {
    const response = await fetch(`/api/clients/${clientSlug}/orders/${orderId}`);
    const order = await response.json();

    document.getElementById("loading").classList.add("hidden");

    if (order.status === "confirmed" || order.payment_status === "succeeded") {
      document.getElementById("success").classList.remove("hidden");
      document.getElementById("order-number").textContent = orderId;
      document.getElementById("customer-email").textContent = order.customer.email;
      if (order.estimated_ready_at) {
        document.getElementById("ready-time").textContent =
          new Date(order.estimated_ready_at).toLocaleTimeString();
      }
    } else {
      document.getElementById("error").classList.remove("hidden");
      document.getElementById("error-message").textContent =
        "Your payment could not be processed.";
    }
  }

  checkStatus();
</script>
```

### Configuration

**Django settings:**
```python
# apps/web/config/settings.py

STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")
```

**Doppler secrets:**
```
STRIPE_SECRET_KEY=sk_test_...      # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Frontend environment:**
```
# sites/{client}/wrangler.toml or .env
PUBLIC_STRIPE_KEY=pk_test_...      # or pk_live_... for production
```

### Testing

```python
# tests/payments/test_webhooks.py

import stripe
from django.test import TestCase, Client
from unittest.mock import patch

class StripeWebhookTests(TestCase):
    @patch("stripe.Webhook.construct_event")
    def test_payment_succeeded_updates_order(self, mock_construct):
        order = OrderFactory(status="pending_payment")

        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test",
                    "metadata": {"order_id": str(order.id)},
                }
            },
        }

        response = self.client.post(
            "/payments/webhooks/stripe",
            content_type="application/json",
            data="{}",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
```

## Dependencies

- 008-J (Order API endpoints that create PaymentIntent)
- 008-I (Checkout UI that embeds Stripe Elements)
- Stripe account with API keys in Doppler

## Progress

*To be updated during implementation*
