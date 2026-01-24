# EP-008: Restaurant Client Type with POS Integration

**Status:** active
**Last Updated:** 2026-01-21
**Tickets:** [View all tickets](../tickets/) (008-A through 008-M)

## Goal

Add restaurants as a first-class client type with POS integration (Toast, Clover, Square), real-time menu synchronization, 86'd item handling, and full online ordering with payments. Design an adapter-based architecture that enables rapid onboarding of new POS providers while supporting static menu fallback for clients without POS integration.

## Summary of Requirements

Based on clarification with the human engineer:

| Requirement | Decision |
|-------------|----------|
| POS Systems | Toast + Clover + Square (adapter-based, mockable) |
| Data Freshness | Real-time webhooks for 86'd items |
| Ordering Scope | Full ordering with payments (Stripe) |
| Credentials | Doppler (per-client project) |
| Static Fallback | Yes - restaurants can launch without POS |
| Budget | No constraints |

## Architecture Review

### Current State

The Consult platform has established patterns that this EP will extend:

1. **Client Sites**: Astro static sites in `sites/{client-slug}/` with `src/config.ts` for per-client configuration
2. **Multi-tenancy**: `ClientScopedModel` base class with `ClientScopedManager` for tenant isolation
3. **Intake Pattern**: Cloudflare Workers → `inbox_submission` table → Django async processing
4. **Webhook Schemas**: Pydantic models in `packages/schemas/` for Cal.com, Twilio, Jobber
5. **Existing Placeholder**: `POSWebhookPayload` in `webhooks.py` (needs expansion)

### What's New for Restaurants

Restaurants introduce domain concepts not present in service-based clients:

- **Menus** with hierarchical structure (Menu → Categories → Items → Modifiers)
- **Inventory state** (86'd/available) that changes in real-time
- **Online ordering** with cart, checkout, and payment processing
- **POS write-back** (orders submitted to POS system)

## Proposed Architecture

### 1. POS Adapter Interface

Create an abstract interface that all POS integrations implement:

```python
# apps/web/pos/adapters/base.py

from abc import ABC, abstractmethod
from typing import Protocol

class POSAdapter(Protocol):
    """Interface for POS system integrations."""

    provider: str  # "toast", "clover", "square"

    # Authentication
    async def authenticate(self, credentials: POSCredentials) -> POSSession: ...
    async def refresh_token(self, session: POSSession) -> POSSession: ...

    # Menu Operations (read)
    async def get_menus(self, location_id: str) -> list[Menu]: ...
    async def get_menu(self, location_id: str, menu_id: str) -> Menu: ...
    async def get_item_availability(self, location_id: str) -> dict[str, bool]: ...

    # Order Operations (write)
    async def create_order(self, location_id: str, order: Order) -> OrderResult: ...
    async def get_order_status(self, location_id: str, order_id: str) -> OrderStatus: ...

    # Webhook Verification
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool: ...
    def parse_webhook(self, payload: dict) -> POSWebhookEvent: ...


class MockPOSAdapter(POSAdapter):
    """Mock adapter for development and testing."""
    provider = "mock"
    # Returns configurable test data
```

### 2. Domain Models

New Django models for restaurant data:

```python
# apps/web/restaurant/models.py

class RestaurantProfile(ClientScopedModel):
    """Restaurant-specific client configuration."""
    pos_provider = models.CharField(choices=POS_PROVIDERS, null=True, blank=True)
    pos_location_id = models.CharField(max_length=255, null=True, blank=True)
    pos_connected_at = models.DateTimeField(null=True, blank=True)

    # Fallback when no POS
    static_menu_json = models.JSONField(null=True, blank=True)

    # Display settings
    show_prices = models.BooleanField(default=True)
    show_descriptions = models.BooleanField(default=True)
    ordering_enabled = models.BooleanField(default=False)


class Menu(ClientScopedModel):
    """A menu (e.g., Breakfast, Lunch, Dinner, Drinks)."""
    external_id = models.CharField(max_length=255, null=True, blank=True)  # POS ID
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    available_start = models.TimeField(null=True, blank=True)  # e.g., 6:00 AM
    available_end = models.TimeField(null=True, blank=True)    # e.g., 11:00 AM


class MenuCategory(ClientScopedModel):
    """Category within a menu (e.g., Appetizers, Entrees)."""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="categories")
    external_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)


class MenuItem(ClientScopedModel):
    """Individual menu item."""
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name="items")
    external_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)

    # Availability
    is_available = models.BooleanField(default=True)  # 86'd when False
    availability_updated_at = models.DateTimeField(auto_now=True)

    # Dietary info
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    allergens = models.JSONField(default=list)  # ["nuts", "dairy", "shellfish"]

    display_order = models.PositiveIntegerField(default=0)


class ModifierGroup(ClientScopedModel):
    """Group of modifiers for an item (e.g., "Choose your protein")."""
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="modifier_groups")
    external_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=200)
    min_selections = models.PositiveIntegerField(default=0)  # 0 = optional
    max_selections = models.PositiveIntegerField(default=1)  # 1 = single choice
    display_order = models.PositiveIntegerField(default=0)


class Modifier(ClientScopedModel):
    """Individual modifier option."""
    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="modifiers")
    external_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=200)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)


class Order(ClientScopedModel):
    """Customer order."""
    external_id = models.CharField(max_length=255, null=True, blank=True)  # POS order ID

    # Customer info
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)

    # Order details
    status = models.CharField(max_length=50, choices=ORDER_STATUSES, default="pending")
    order_type = models.CharField(max_length=50, choices=ORDER_TYPES)  # pickup, delivery
    scheduled_time = models.DateTimeField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    payment_status = models.CharField(max_length=50, default="pending")

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class OrderItem(ClientScopedModel):
    """Line item in an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    modifiers = models.JSONField(default=list)  # Snapshot of selected modifiers
    special_instructions = models.TextField(blank=True)
```

### 3. Webhook Handler Architecture

Extend the intake worker to handle POS webhooks:

```
POST /intake/{client_slug}/pos/{provider}
  - /intake/tonys-pizza/pos/toast
  - /intake/marias-cafe/pos/clover
  - /intake/burger-barn/pos/square
```

Webhook processing flow:
```
POS System → Intake Worker → pos_webhook_submission table
                              ↓ (Django async task)
                          Verify signature
                          Parse event type
                          Route to handler:
                            - menu_updated → sync full menu
                            - item_86d → update MenuItem.is_available
                            - order_status_changed → update Order.status
```

### 4. Menu Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                            │
├─────────────────────────────────────────────────────────────┤
│  POS Integration          │  Static Fallback                │
│  ─────────────────        │  ──────────────                 │
│  Toast/Clover/Square API  │  RestaurantProfile.static_menu  │
│  Real-time webhooks       │  Manual JSON upload             │
│  86'd via webhook         │  Redeploy to update             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django Backend                           │
├─────────────────────────────────────────────────────────────┤
│  Menu/MenuItem/Modifier models (canonical source)           │
│  API endpoints: GET /api/menu, GET /api/menu/{id}/items     │
│  Availability endpoint: GET /api/availability (polled)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Astro Frontend                           │
├─────────────────────────────────────────────────────────────┤
│  Build-time: Fetch full menu structure for SSG              │
│  Runtime: Poll /api/availability every 60s for 86'd status  │
│  Client-side: Update UI to gray out unavailable items       │
└─────────────────────────────────────────────────────────────┘
```

### 5. Online Ordering Flow

```
Customer                    Astro Site                 Django API               POS System
   │                           │                           │                        │
   │  Browse menu              │                           │                        │
   │ ─────────────────────────>│                           │                        │
   │                           │  GET /api/menu            │                        │
   │                           │ ─────────────────────────>│                        │
   │                           │  Menu data (SSG cached)   │                        │
   │                           │ <─────────────────────────│                        │
   │  Add items to cart        │                           │                        │
   │ ─────────────────────────>│  (client-side state)      │                        │
   │                           │                           │                        │
   │  Checkout                 │                           │                        │
   │ ─────────────────────────>│                           │                        │
   │                           │  POST /api/orders         │                        │
   │                           │ ─────────────────────────>│                        │
   │                           │                           │  Create order          │
   │                           │                           │ ───────────────────────>
   │                           │                           │  Order ID              │
   │                           │                           │ <───────────────────────
   │                           │  Stripe PaymentIntent     │                        │
   │                           │ <─────────────────────────│                        │
   │  Enter payment            │                           │                        │
   │ ─────────────────────────>│  Stripe.js                │                        │
   │                           │ ─────────────────────────>│  (Stripe webhook)      │
   │                           │                           │                        │
   │                           │  POST /api/orders/confirm │                        │
   │                           │ ─────────────────────────>│                        │
   │                           │                           │  Update order status   │
   │                           │                           │ ───────────────────────>
   │  Order confirmed          │                           │                        │
   │ <─────────────────────────│                           │                        │
```

### 6. Site Configuration Extension

Extend `SiteConfig` for restaurant clients:

```typescript
// sites/{restaurant-slug}/src/config.ts

export interface RestaurantConfig extends SiteConfig {
  restaurant: {
    // Core info
    cuisine: string[];  // ["Italian", "Pizza"]
    priceRange: "$" | "$$" | "$$$" | "$$$$";

    // Hours (can be complex for restaurants)
    hours: {
      [day: string]: { open: string; close: string }[] | "closed";
    };

    // Features
    features: {
      dineIn: boolean;
      takeout: boolean;
      delivery: boolean;
      reservations: boolean;
      onlineOrdering: boolean;
    };

    // Integration
    pos?: {
      provider: "toast" | "clover" | "square" | null;
      locationId: string;
    };

    // Delivery (if applicable)
    delivery?: {
      radius: number;  // miles
      minimumOrder: number;
      fee: number;
    };

    // Reservations (if applicable)
    reservations?: {
      provider: "resy" | "opentable" | "calcom" | null;
      url: string;
    };
  };
}
```

### 7. Directory Structure Changes

```
apps/web/
├── pos/                          # NEW: POS integration module
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py              # POSAdapter protocol
│   │   ├── mock.py              # MockPOSAdapter for testing
│   │   ├── toast.py             # ToastAdapter
│   │   ├── clover.py            # CloverAdapter
│   │   └── square.py            # SquareAdapter
│   ├── services/
│   │   ├── __init__.py
│   │   ├── menu_sync.py         # Full menu synchronization
│   │   ├── availability.py      # 86'd item handling
│   │   └── order_submit.py      # Order submission to POS
│   └── webhooks/
│       ├── __init__.py
│       ├── handlers.py          # Event type routing
│       └── validators.py        # Signature verification
│
├── restaurant/                   # NEW: Restaurant domain models
│   ├── __init__.py
│   ├── admin.py
│   ├── models.py                # Menu, MenuItem, Order, etc.
│   ├── serializers.py           # DRF serializers
│   ├── views.py                 # API endpoints
│   ├── urls.py
│   └── migrations/
│
├── payments/                     # NEW: Stripe integration
│   ├── __init__.py
│   ├── services.py              # PaymentIntent creation
│   ├── webhooks.py              # Stripe webhook handlers
│   └── views.py

packages/schemas/consult_schemas/
├── pos.py                        # NEW: POS-specific schemas
│   ├── POSCredentials
│   ├── Menu, MenuItem, Modifier
│   ├── Order, OrderItem
│   └── POSWebhookEvent (specialized per provider)
│
├── restaurant.py                 # NEW: Restaurant config schemas
│   └── RestaurantConfig

sites/
├── _template-restaurant/         # NEW: Restaurant site template
│   ├── src/
│   │   ├── config.ts            # RestaurantConfig type
│   │   ├── pages/
│   │   │   ├── index.astro      # Homepage with hours, cuisine
│   │   │   ├── menu.astro       # Menu display page
│   │   │   ├── order.astro      # Online ordering (if enabled)
│   │   │   └── contact.astro
│   │   ├── components/
│   │   │   ├── MenuSection.astro
│   │   │   ├── MenuItem.astro
│   │   │   ├── Cart.astro       # Client-side cart
│   │   │   ├── Checkout.astro
│   │   │   └── AvailabilityBadge.astro  # 86'd indicator
│   │   └── lib/
│   │       ├── menu.ts          # Menu data fetching
│   │       ├── cart.ts          # Cart state management
│   │       └── availability.ts  # Polling for 86'd status

workers/intake/
├── src/
│   ├── routes/
│   │   ├── form.ts
│   │   ├── sms.ts
│   │   ├── voice.ts
│   │   └── pos.ts               # NEW: POS webhook handler
```

### 8. New Dependencies

**Python (pyproject.toml):**
```toml
[project.dependencies]
stripe = "^7.0"           # Stripe payments
httpx = "^0.27"           # Async HTTP for POS APIs

[project.optional-dependencies]
pos-toast = ["toast-api-client"]      # If official SDK exists
pos-clover = ["clover-sdk"]           # If official SDK exists
```

**TypeScript (sites):**
```json
{
  "dependencies": {
    "@stripe/stripe-js": "^2.0"    // Client-side Stripe
  }
}
```

## Tickets

| ID | Title | Phase | Status |
|----|-------|-------|--------|
| [008-A](../tickets/008-A-pos-adapter-interface.md) | POS adapter interface and mock implementation | 1 | complete |
| [008-B](../tickets/008-B-restaurant-domain-models.md) | Restaurant domain models and migrations | 1 | complete |
| [008-C](../tickets/008-C-menu-api-endpoints.md) | Menu API endpoints | 1 | complete |
| [008-D](../tickets/008-D-restaurant-site-template.md) | Restaurant site template (menu display) | 1 | complete |
| [008-E](../tickets/008-E-availability-webhook-polling.md) | 86'd item webhook handler and availability polling | 2 | complete |
| [008-F](../tickets/008-F-toast-adapter.md) | Toast adapter implementation | 2 | complete |
| [008-G](../tickets/008-G-clover-adapter.md) | Clover adapter implementation | 3 | complete |
| [008-H](../tickets/008-H-square-adapter.md) | Square adapter implementation | 3 | complete |
| [008-I](../tickets/008-I-cart-checkout-components.md) | Cart and checkout frontend components | 4 | pending |
| [008-J](../tickets/008-J-order-api-endpoints.md) | Order API endpoints | 4 | pending |
| [008-K](../tickets/008-K-stripe-payment-integration.md) | Stripe payment integration | 4 | pending |
| [008-L](../tickets/008-L-order-submission-pos.md) | Order submission to POS | 4 | pending |
| [008-M](../tickets/008-M-first-restaurant-deployment.md) | First restaurant client deployment | 5 | pending |

## Implementation Phases

### Phase 1: Foundation
**Tickets:** [008-A](../tickets/008-A-pos-adapter-interface.md), [008-B](../tickets/008-B-restaurant-domain-models.md), [008-C](../tickets/008-C-menu-api-endpoints.md), [008-D](../tickets/008-D-restaurant-site-template.md)
**Goal:** Menu display with static fallback

- Define POS adapter protocol with mock implementation
- Create restaurant domain models (Menu, MenuItem, ModifierGroup, Modifier)
- Build menu API endpoints (GET /api/clients/{slug}/menu)
- Create restaurant site template with menu display
- Support static menu JSON for non-POS clients

**Demo value:** Can deploy restaurant sites with manually-maintained menus.

### Phase 2: POS Read Integration
**Tickets:** [008-E](../tickets/008-E-availability-webhook-polling.md), [008-F](../tickets/008-F-toast-adapter.md)
**Goal:** Live menu sync with Toast

- Implement Toast adapter (menu fetching)
- Add webhook handler for menu updates
- Implement 86'd item handling (webhook → DB → frontend polling)
- Build availability polling endpoint and frontend component

**Demo value:** Restaurant menu stays in sync with Toast POS, 86'd items update in real-time.

### Phase 3: Additional POS Providers
**Tickets:** [008-G](../tickets/008-G-clover-adapter.md), [008-H](../tickets/008-H-square-adapter.md)
**Goal:** Clover and Square support

- Implement Clover adapter
- Implement Square adapter
- Verify adapter interface consistency across providers

**Demo value:** Can onboard restaurants using any of the three major POS systems.

### Phase 4: Online Ordering
**Tickets:** [008-I](../tickets/008-I-cart-checkout-components.md), [008-J](../tickets/008-J-order-api-endpoints.md), [008-K](../tickets/008-K-stripe-payment-integration.md), [008-L](../tickets/008-L-order-submission-pos.md)
**Goal:** Full ordering with payments

- Build cart component (client-side state)
- Build checkout flow with customer info collection
- Integrate Stripe for payments
- Create order API endpoints
- Implement order submission to POS
- Add order status tracking

**Demo value:** End-to-end online ordering with payment processing and POS integration.

### Phase 5: Production Deployment
**Tickets:** [008-M](../tickets/008-M-first-restaurant-deployment.md)
**Goal:** First live restaurant client

- Deploy first restaurant client site
- Configure POS integration in production
- Monitor and iterate

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Adapter pattern | Protocol-based with mock | Enables testing without POS credentials, allows easy addition of new providers |
| Menu storage | Django models (not just cache) | Need to support static fallback, track availability history, audit trail |
| 86'd updates | Real-time webhooks + frontend polling | Webhooks for push updates, polling as fallback and for non-webhook scenarios |
| Payments | Stripe (not POS payment) | Consistent experience across POS providers, better developer experience |
| Order flow | API-first | Astro fetches at build time, client-side cart, API for checkout - allows SSG benefits |
| Cart state | Client-side (localStorage) | No login required for ordering, cart persists across page loads |

## Risks and Open Items

### Technical Risks

1. **POS API Access**
   - Toast requires partnership application for full API access
   - May need to start with "Standard API Access" (read-only) and apply for partner access
   - Mitigation: Begin Toast partnership application immediately; mock adapter enables frontend development

2. **Webhook Reliability**
   - POS webhooks may be delayed or fail
   - Mitigation: Implement polling fallback for menu sync; idempotent webhook handlers

3. **Payment ↔ POS Synchronization**
   - Stripe payment confirmation and POS order creation are separate operations
   - Risk of payment taken but order not created in POS
   - Mitigation: Implement saga pattern with compensation (refund if POS fails)

4. **Rate Limits**
   - Toast: 1 req/sec per location for menus endpoint
   - Mitigation: Aggressive caching; batch updates; don't poll unnecessarily

### Open Questions

1. **Order Type Support**
   - Do we support delivery in Phase 4, or just pickup?
   - Delivery adds complexity: address validation, delivery zones, driver coordination
   - **Recommendation:** Pickup only in initial release; delivery as future enhancement

2. **Tax Calculation**
   - Use POS tax calculation vs. Stripe Tax vs. manual configuration?
   - **Recommendation:** Use POS tax calculation when available; fall back to Stripe Tax

3. **Menu Photos**
   - POS systems may not have high-quality photos
   - Allow manual override/upload for menu item images?
   - **Recommendation:** Yes, store image_url override in MenuItem model

4. **Inventory Granularity**
   - Some POS systems track inventory at modifier level (e.g., "out of chicken")
   - Do we need modifier-level availability?
   - **Recommendation:** Yes, track is_available on Modifier model

5. **Multi-Location Support**
   - Some restaurant clients may have multiple locations
   - Current Client model is single-tenant (one location per client)
   - **Recommendation:** Defer to future EP; use separate Client per location initially

### Dependencies

- [ ] EP-006 (Dagger pipeline) - needed for reliable deployments
- [ ] EP-007 (Pulumi infra) - needed for production deployment
- [ ] Toast partnership application submitted and approved (for write access)

## Progress Log

### 2026-01-21
- EP drafted with full architecture review
- Requirements clarified: adapter-based POS (Toast+Clover+Square), real-time webhooks, full ordering with Stripe, static fallback
- All 13 tickets created (008-A through 008-M)
- Tickets organized into 5 phases
- Roadmap updated with phase structure

### 2026-01-23
- **008-A complete**: POS adapter interface and mock implementation
  - POSAdapter protocol in `apps/web/pos/adapters/base.py`
  - MockPOSAdapter with configurable menus, 86'd items, order simulation
  - POS schemas in `packages/schemas/consult_schemas/pos.py`
  - 27 unit tests, all passing
  - Added pytest-asyncio for async test support

- **008-B complete**: Restaurant domain models and migrations
  - 8 models: RestaurantProfile, Menu, MenuCategory, MenuItem, ModifierGroup, Modifier, Order, OrderItem
  - All inherit from ClientScopedModel with proper indexes
  - Admin registration with inline editing
  - Factory classes for testing
  - 26 unit tests, all passing

- **008-C complete**: Menu API endpoints
  - Pydantic schemas for nested menu serialization in `apps/web/restaurant/serializers.py`
  - Three public API endpoints in `apps/web/restaurant/views.py`:
    - `GET /api/clients/{slug}/menu` - Full menu structure (5min cache)
    - `GET /api/clients/{slug}/menu/{menu_id}` - Single menu (5min cache)
    - `GET /api/clients/{slug}/availability` - Item/modifier availability (30s cache)
  - CORS enabled for Astro site access
  - Static fallback via `RestaurantProfile.static_menu_json`
  - 18 integration tests, all passing

- **008-D complete**: Restaurant site template
  - Full Astro template in `sites/_template-restaurant/`
  - `RestaurantConfig` type with hours, cuisine, features, POS config
  - Components: Hours, MenuItem, MenuSection, MenuNav, DietaryBadges, AllergenInfo
  - Pages: Homepage (hero, hours, location), Menu (with polling), Contact
  - Build-time menu fetch with mock data fallback
  - 60-second availability polling for 86'd items
  - Schema.org/Restaurant structured data
  - Warm color theme (DaisyUI)
  - Build verified: 3 pages built successfully

**Phase 1 complete!** All foundation tickets done (008-A through 008-D).

- **008-G complete**: Clover adapter implementation
  - Full `CloverAdapter` in `apps/web/pos/adapters/clover.py`
  - OAuth 2.0 merchant authorization flow
  - Menu operations via categories/items endpoints
  - Item availability via item_stocks endpoint
  - Webhook handling (ITEM, CATEGORY, inventory events)
  - Environment switching (sandbox/production)
  - 38 unit tests, all passing
  - Adapter registry updated

- **008-H complete**: Square adapter implementation
  - Full `SquareAdapter` in `apps/web/pos/adapters/square.py`
  - OAuth 2.0 with actual token refresh (tokens expire, unlike Clover)
  - Catalog API with pagination handling
  - Items have variations with prices at variation level
  - Inventory uses both quantity and state for availability
  - Webhook signature uses URL + body (unique to Square)
  - Webhook handling (inventory.count.updated, catalog.version.updated)
  - Environment switching (sandbox/production)
  - Rate limiting (10 req/sec) with exponential backoff
  - 39 unit tests, all passing
  - Adapter registry updated

**Phase 3 complete!** All POS adapter tickets done (008-G and 008-H).

**Next steps:**
- Phase 4: Online ordering (008-I through 008-L)
  - Cart and checkout frontend components
  - Order API endpoints
  - Stripe payment integration
  - Order submission to POS

## Retrospective

*To be completed after implementation*

---

## Appendix: POS API Reference

### Toast API

**Authentication:** OAuth 2.0 client credentials
```
POST https://ws-api.toasttab.com/authentication/v1/authentication/login
{
  "clientId": "...",
  "clientSecret": "...",
  "userAccessType": "TOAST_MACHINE_CLIENT"
}
```

**Menu Endpoint:**
```
GET https://ws-api.toasttab.com/menus/v2/menus/{restaurantGuid}
Response: Full menu tree with groups, items, modifiers
```

**Webhooks:**
- `MENU_UPDATED` - Full menu sync needed
- `ITEM_AVAILABILITY_CHANGED` - 86'd status change
- `ORDER_STATUS_CHANGED` - Order progress updates

### Clover API

**Authentication:** OAuth 2.0 with merchant authorization
```
GET https://sandbox.dev.clover.com/oauth/authorize?client_id=...&redirect_uri=...
POST https://sandbox.dev.clover.com/oauth/token
```

**Menu Endpoint:**
```
GET https://api.clover.com/v3/merchants/{mId}/items
GET https://api.clover.com/v3/merchants/{mId}/categories
```

### Square API

**Authentication:** OAuth 2.0
```
POST https://connect.squareup.com/oauth2/token
```

**Menu Endpoint (Catalog API):**
```
POST https://connect.squareup.com/v2/catalog/search
{
  "object_types": ["ITEM", "CATEGORY", "MODIFIER_LIST"]
}
```
