# 008-A: POS Adapter Interface and Mock Implementation

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 1 (Foundation)

## Summary

Define the abstract POS adapter protocol that all POS integrations will implement. Create a mock adapter for development and testing that returns configurable test data without requiring real POS credentials.

## Acceptance Criteria

- [x] `POSAdapter` protocol defined in `apps/web/pos/adapters/base.py`
- [x] Protocol includes authentication methods (`authenticate`, `refresh_token`)
- [x] Protocol includes menu operations (`get_menus`, `get_menu`, `get_item_availability`)
- [x] Protocol includes order operations (`create_order`, `get_order_status`)
- [x] Protocol includes webhook methods (`verify_webhook_signature`, `parse_webhook`)
- [x] `MockPOSAdapter` implementation that returns configurable test data
- [x] Mock adapter supports simulating 86'd items
- [x] Mock adapter supports simulating order creation success/failure
- [x] Unit tests for mock adapter
- [x] Type hints pass mypy strict mode

## Implementation Notes

### Directory Structure

```
apps/web/pos/
├── __init__.py
├── adapters/
│   ├── __init__.py
│   ├── base.py          # POSAdapter protocol + supporting types
│   └── mock.py          # MockPOSAdapter
└── exceptions.py        # POSAuthError, POSAPIError, etc.
```

### Key Types

```python
# base.py
from typing import Protocol

class POSCredentials(BaseModel):
    provider: str
    client_id: str
    client_secret: str
    location_id: str
    # Provider-specific fields as extras

class POSSession(BaseModel):
    provider: str
    access_token: str
    refresh_token: str | None
    expires_at: datetime

class POSAdapter(Protocol):
    provider: str

    async def authenticate(self, credentials: POSCredentials) -> POSSession: ...
    async def refresh_token(self, session: POSSession) -> POSSession: ...
    async def get_menus(self, location_id: str) -> list[POSMenu]: ...
    async def get_menu(self, location_id: str, menu_id: str) -> POSMenu: ...
    async def get_item_availability(self, location_id: str) -> dict[str, bool]: ...
    async def create_order(self, location_id: str, order: POSOrder) -> POSOrderResult: ...
    async def get_order_status(self, location_id: str, order_id: str) -> POSOrderStatus: ...
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool: ...
    def parse_webhook(self, payload: dict) -> POSWebhookEvent: ...
```

### Mock Adapter Features

```python
# mock.py
class MockPOSAdapter:
    def __init__(
        self,
        menus: list[POSMenu] | None = None,
        unavailable_items: set[str] | None = None,
        fail_orders: bool = False,
        auth_delay_ms: int = 0,
    ): ...
```

### Shared Schemas

Also add POS-specific schemas to `packages/schemas/consult_schemas/pos.py`:
- `POSMenu`, `POSMenuCategory`, `POSMenuItem`, `POSModifierGroup`, `POSModifier`
- `POSOrder`, `POSOrderItem`, `POSOrderResult`, `POSOrderStatus`
- `POSWebhookEvent` with discriminated union for event types

## Dependencies

- None (foundation ticket)

## Progress

### 2026-01-23

**Completed implementation:**

1. **Created `apps/web/pos/` module structure:**
   - `__init__.py` - Module docstring
   - `apps.py` - Django app config
   - `exceptions.py` - POSError, POSAuthError, POSAPIError, POSWebhookError, POSOrderError, POSRateLimitError
   - `adapters/__init__.py` - Exports POSAdapter and MockPOSAdapter
   - `adapters/base.py` - POSAdapter protocol with full type hints
   - `adapters/mock.py` - MockPOSAdapter implementation

2. **Added POS schemas to `packages/schemas/consult_schemas/pos.py`:**
   - Enums: POSProvider, OrderType, OrderStatus, PaymentStatus
   - Authentication: POSCredentials, POSSession
   - Menu data: POSMenu, POSMenuCategory, POSMenuItem, POSModifierGroup, POSModifier
   - Orders: POSOrder, POSOrderItem, POSOrderItemModifier, POSOrderResult, POSOrderStatus
   - Webhooks: POSWebhookEvent (union of MenuUpdatedEvent, ItemAvailabilityChangedEvent, OrderStatusChangedEvent)

3. **MockPOSAdapter features:**
   - Configurable test menus (defaults to breakfast/lunch menus)
   - Simulated 86'd items via `set_item_unavailable()`/`set_item_available()`
   - Configurable order failure via `fail_orders` parameter
   - Configurable auth failure via `fail_auth` parameter
   - Simulated delays via `auth_delay_ms`/`api_delay_ms` parameters
   - Order status tracking with `set_order_status()`
   - HMAC-SHA256 webhook signature verification

4. **Unit tests (27 tests, all passing):**
   - Authentication (success, failure, token refresh)
   - Menu operations (get all, get by ID, not found, custom menus)
   - Item availability (mark unavailable, reflected in menus)
   - Order operations (create, failure, unavailable items, status tracking)
   - Webhook handling (signature verification, event parsing)

5. **Quality checks:**
   - ruff check: ✓
   - ruff format: ✓
   - mypy (strict mode): ✓
   - pytest: 27 tests passing

**Dependencies added:**
- `pytest-asyncio` for async test support
- Configured `asyncio_mode = "auto"` in pyproject.toml
