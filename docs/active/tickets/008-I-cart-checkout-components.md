# 008-I: Cart and Checkout Frontend Components

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 4 (Online Ordering)

## Summary

Build the client-side cart and checkout UI components for the restaurant site template. Cart state is managed in localStorage (no login required). Checkout collects customer info and prepares for Stripe payment.

## Acceptance Criteria

- [ ] Cart state management in localStorage
- [ ] "Add to Cart" buttons on menu items
- [ ] Modifier selection modal/drawer
- [ ] Cart drawer/sidebar showing items and totals
- [ ] Quantity adjustment (+/-)
- [ ] Item removal from cart
- [ ] Special instructions per item
- [ ] Cart badge showing item count
- [ ] Checkout page with customer info form
- [ ] Order type selection (pickup/delivery if enabled)
- [ ] Pickup time selection
- [ ] Tip selection (preset amounts + custom)
- [ ] Order summary before payment
- [ ] 86'd items blocked from cart
- [ ] Mobile-responsive design
- [ ] Cart persists across page navigation
- [ ] Unit tests for cart logic

## Implementation Notes

### Directory Structure

```
sites/_template-restaurant/src/
├── components/
│   ├── cart/
│   │   ├── CartProvider.astro    # Context wrapper (or use nanostores)
│   │   ├── CartDrawer.astro      # Slide-out cart panel
│   │   ├── CartItem.astro        # Line item in cart
│   │   ├── CartBadge.astro       # Item count indicator
│   │   └── CartTotals.astro      # Subtotal, tax, tip, total
│   ├── menu/
│   │   ├── AddToCartButton.astro
│   │   └── ModifierModal.astro   # Modifier selection
│   └── checkout/
│       ├── CustomerForm.astro    # Name, email, phone
│       ├── OrderTypeSelector.astro
│       ├── PickupTimeSelector.astro
│       ├── TipSelector.astro
│       └── OrderSummary.astro
├── pages/
│   └── checkout.astro
└── lib/
    ├── cart.ts                   # Cart state management
    └── checkout.ts               # Checkout validation/submission
```

### Cart State Management

Using nanostores for reactive state that persists to localStorage:

```typescript
// src/lib/cart.ts
import { persistentAtom } from "@nanostores/persistent";
import { computed } from "nanostores";

export interface CartItem {
  id: string;               // Unique cart item ID (UUID)
  menuItemId: number;       // MenuItem.id from API
  name: string;
  price: number;            // Unit price with modifiers
  quantity: number;
  modifiers: {
    groupId: number;
    groupName: string;
    selections: {
      id: number;
      name: string;
      priceAdjustment: number;
    }[];
  }[];
  specialInstructions: string;
}

export interface CartState {
  items: CartItem[];
  orderType: "pickup" | "delivery";
  scheduledTime: string | null;
  specialInstructions: string;
  tip: number;
}

export const cart = persistentAtom<CartState>(
  "restaurant-cart",
  {
    items: [],
    orderType: "pickup",
    scheduledTime: null,
    specialInstructions: "",
    tip: 0,
  },
  {
    encode: JSON.stringify,
    decode: JSON.parse,
  }
);

// Computed values
export const cartItemCount = computed(cart, (state) =>
  state.items.reduce((sum, item) => sum + item.quantity, 0)
);

export const cartSubtotal = computed(cart, (state) =>
  state.items.reduce((sum, item) => sum + item.price * item.quantity, 0)
);

// Actions
export function addToCart(item: Omit<CartItem, "id">) {
  const current = cart.get();
  cart.set({
    ...current,
    items: [
      ...current.items,
      { ...item, id: crypto.randomUUID() },
    ],
  });
}

export function updateQuantity(itemId: string, quantity: number) {
  const current = cart.get();
  if (quantity <= 0) {
    removeFromCart(itemId);
    return;
  }
  cart.set({
    ...current,
    items: current.items.map((item) =>
      item.id === itemId ? { ...item, quantity } : item
    ),
  });
}

export function removeFromCart(itemId: string) {
  const current = cart.get();
  cart.set({
    ...current,
    items: current.items.filter((item) => item.id !== itemId),
  });
}

export function clearCart() {
  cart.set({
    items: [],
    orderType: "pickup",
    scheduledTime: null,
    specialInstructions: "",
    tip: 0,
  });
}

export function setTip(amount: number) {
  cart.set({ ...cart.get(), tip: amount });
}
```

### Add to Cart Flow

```astro
<!-- AddToCartButton.astro -->
---
interface Props {
  item: MenuItem;
}
const { item } = Astro.props;
const hasModifiers = item.modifier_groups?.length > 0;
---

<button
  class="btn btn-primary"
  data-item={JSON.stringify(item)}
  data-has-modifiers={hasModifiers}
  disabled={!item.is_available}
>
  {item.is_available ? "Add to Cart" : "Unavailable"}
</button>

<script>
  import { addToCart } from "../lib/cart";

  document.querySelectorAll("[data-item]").forEach((button) => {
    button.addEventListener("click", (e) => {
      const item = JSON.parse(button.dataset.item);
      const hasModifiers = button.dataset.hasModifiers === "true";

      if (hasModifiers) {
        // Open modifier modal
        window.dispatchEvent(
          new CustomEvent("open-modifier-modal", { detail: item })
        );
      } else {
        // Add directly
        addToCart({
          menuItemId: item.id,
          name: item.name,
          price: parseFloat(item.price),
          quantity: 1,
          modifiers: [],
          specialInstructions: "",
        });
        // Show toast notification
        window.dispatchEvent(new CustomEvent("cart-updated"));
      }
    });
  });
</script>
```

### Modifier Selection Modal

```astro
<!-- ModifierModal.astro -->
---
---
<dialog id="modifier-modal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg" id="modal-item-name"></h3>

    <div id="modifier-groups" class="py-4">
      <!-- Populated dynamically -->
    </div>

    <div class="form-control">
      <label class="label">Special Instructions</label>
      <textarea
        id="special-instructions"
        class="textarea textarea-bordered"
        placeholder="Any special requests?"
      ></textarea>
    </div>

    <div class="modal-action">
      <button class="btn" onclick="document.getElementById('modifier-modal').close()">
        Cancel
      </button>
      <button class="btn btn-primary" id="add-with-modifiers">
        Add to Cart
      </button>
    </div>
  </div>
</dialog>

<script>
  // Modal logic for modifier selection
  // Validates min/max selections per group
  // Calculates total price with modifiers
  // Calls addToCart with full item details
</script>
```

### Cart Drawer

```astro
<!-- CartDrawer.astro -->
---
---
<div id="cart-drawer" class="drawer drawer-end">
  <input id="cart-drawer-toggle" type="checkbox" class="drawer-toggle" />
  <div class="drawer-side z-50">
    <label for="cart-drawer-toggle" class="drawer-overlay"></label>
    <div class="bg-base-100 w-80 min-h-full p-4">
      <h2 class="text-xl font-bold mb-4">Your Order</h2>

      <div id="cart-items" class="space-y-4">
        <!-- Populated by cart state -->
      </div>

      <div id="cart-empty" class="text-center py-8 text-gray-500">
        Your cart is empty
      </div>

      <div id="cart-footer" class="mt-4 pt-4 border-t">
        <div class="flex justify-between mb-2">
          <span>Subtotal</span>
          <span id="cart-subtotal">$0.00</span>
        </div>
        <a href="/checkout" class="btn btn-primary w-full">
          Checkout
        </a>
      </div>
    </div>
  </div>
</div>

<script>
  import { cart, cartSubtotal } from "../lib/cart";

  // Subscribe to cart changes and update UI
  cart.subscribe((state) => {
    renderCartItems(state.items);
    updateSubtotal(cartSubtotal.get());
  });
</script>
```

### Checkout Page

```astro
<!-- pages/checkout.astro -->
---
import RestaurantLayout from "../layouts/RestaurantLayout.astro";
import CustomerForm from "../components/checkout/CustomerForm.astro";
import OrderTypeSelector from "../components/checkout/OrderTypeSelector.astro";
import PickupTimeSelector from "../components/checkout/PickupTimeSelector.astro";
import TipSelector from "../components/checkout/TipSelector.astro";
import OrderSummary from "../components/checkout/OrderSummary.astro";
---

<RestaurantLayout title="Checkout">
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Checkout</h1>

    <div class="grid lg:grid-cols-2 gap-8">
      <div class="space-y-6">
        <CustomerForm />
        <OrderTypeSelector />
        <PickupTimeSelector />
        <TipSelector />
      </div>

      <div>
        <OrderSummary />
        <div id="payment-element" class="mt-6">
          <!-- Stripe Elements injected here -->
        </div>
        <button id="submit-order" class="btn btn-primary w-full mt-4">
          Place Order
        </button>
      </div>
    </div>
  </div>
</RestaurantLayout>

<script>
  // Checkout form validation
  // Stripe Elements initialization (see 008-K)
  // Order submission
</script>
```

### 86'd Item Handling

Cart must check availability before allowing add:

```typescript
// src/lib/cart.ts

export function canAddToCart(
  menuItemId: number,
  availability: Record<string, boolean>
): boolean {
  return availability[menuItemId.toString()] !== false;
}

// Called before addToCart
if (!canAddToCart(item.id, currentAvailability)) {
  showError("This item is currently unavailable");
  return;
}
```

Also periodically validate cart against availability and notify user of any items that became unavailable.

## Dependencies

- 008-D (Restaurant site template)
- 008-C (Menu API for item data)
- nanostores + @nanostores/persistent packages

## Progress

*To be updated during implementation*
