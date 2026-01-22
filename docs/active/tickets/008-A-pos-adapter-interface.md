# 008-A: POS Adapter Interface and Mock Implementation

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 1 (Foundation)

## Summary

Define the abstract POS adapter protocol that all POS integrations will implement. Create a mock adapter for development and testing that returns configurable test data without requiring real POS credentials.

## Acceptance Criteria

- [ ] `POSAdapter` protocol defined in `apps/web/pos/adapters/base.py`
- [ ] Protocol includes authentication methods (`authenticate`, `refresh_token`)
- [ ] Protocol includes menu operations (`get_menus`, `get_menu`, `get_item_availability`)
- [ ] Protocol includes order operations (`create_order`, `get_order_status`)
- [ ] Protocol includes webhook methods (`verify_webhook_signature`, `parse_webhook`)
- [ ] `MockPOSAdapter` implementation that returns configurable test data
- [ ] Mock adapter supports simulating 86'd items
- [ ] Mock adapter supports simulating order creation success/failure
- [ ] Unit tests for mock adapter
- [ ] Type hints pass mypy strict mode

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

*To be updated during implementation*
