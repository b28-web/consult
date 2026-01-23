# 008-F: Toast Adapter Implementation

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 2 (POS Read Integration)

## Summary

Implement the Toast POS adapter following the `POSAdapter` protocol. This includes OAuth authentication, menu fetching, and webhook parsing. Order creation will be added in Phase 4.

## Acceptance Criteria

- [x] `ToastAdapter` class implementing `POSAdapter` protocol
- [x] OAuth 2.0 client credentials authentication
- [x] Token refresh handling (raises error - Toast doesn't support refresh tokens)
- [x] `get_menus()` - Fetch all menus for a location
- [x] `get_menu()` - Fetch single menu with items and modifiers
- [x] `get_item_availability()` - Fetch current 86'd status
- [x] `verify_webhook_signature()` - HMAC validation
- [x] `parse_webhook()` - Convert Toast events to internal format
- [x] Rate limiting (1 req/sec per location)
- [x] Error handling for API failures
- [x] Retry logic with exponential backoff
- [x] Unit tests with mocked HTTP responses (35 tests)
- [x] Adapter registry (`get_adapter()`) for drop-in provider selection
- [ ] Integration test with Toast sandbox (deferred - no dev access)

## Implementation Notes

### Toast API Reference

**Authentication:**
```
POST https://ws-api.toasttab.com/authentication/v1/authentication/login
Content-Type: application/json

{
  "clientId": "{{clientId}}",
  "clientSecret": "{{clientSecret}}",
  "userAccessType": "TOAST_MACHINE_CLIENT"
}

Response:
{
  "token": {
    "accessToken": "...",
    "expiresIn": 86400
  }
}
```

**Menus Endpoint:**
```
GET https://ws-api.toasttab.com/menus/v2/menus
Headers:
  Authorization: Bearer {{accessToken}}
  Toast-Restaurant-External-ID: {{restaurantGuid}}

Response: Full menu tree with groups, items, modifiers
```

**Webhooks:**
- Signature header: `Toast-Signature`
- Algorithm: HMAC-SHA256
- Events: `MENU_UPDATED`, `ITEM_AVAILABILITY_CHANGED`

### Adapter Implementation

```python
# apps/web/pos/adapters/toast.py

import httpx
from datetime import datetime, timedelta

class ToastAdapter:
    provider = "toast"

    BASE_URL = "https://ws-api.toasttab.com"
    AUTH_URL = f"{BASE_URL}/authentication/v1/authentication/login"
    MENUS_URL = f"{BASE_URL}/menus/v2/menus"

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client or httpx.AsyncClient()
        self._rate_limiter = RateLimiter(requests_per_second=1)

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        response = await self._client.post(
            self.AUTH_URL,
            json={
                "clientId": credentials.client_id,
                "clientSecret": credentials.client_secret,
                "userAccessType": "TOAST_MACHINE_CLIENT",
            },
        )
        response.raise_for_status()
        data = response.json()

        return POSSession(
            provider=self.provider,
            access_token=data["token"]["accessToken"],
            refresh_token=None,  # Toast doesn't use refresh tokens
            expires_at=datetime.now() + timedelta(seconds=data["token"]["expiresIn"]),
        )

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        await self._rate_limiter.acquire()

        response = await self._client.get(
            self.MENUS_URL,
            headers={
                "Authorization": f"Bearer {session.access_token}",
                "Toast-Restaurant-External-ID": location_id,
            },
        )
        response.raise_for_status()

        return [self._parse_menu(m) for m in response.json()]

    def _parse_menu(self, raw: dict) -> POSMenu:
        """Convert Toast menu format to internal POSMenu."""
        return POSMenu(
            external_id=raw["guid"],
            name=raw["name"],
            description=raw.get("description", ""),
            categories=[
                self._parse_category(g) for g in raw.get("menuGroups", [])
            ],
        )

    def _parse_category(self, raw: dict) -> POSMenuCategory:
        return POSMenuCategory(
            external_id=raw["guid"],
            name=raw["name"],
            items=[self._parse_item(i) for i in raw.get("menuItems", [])],
        )

    def _parse_item(self, raw: dict) -> POSMenuItem:
        return POSMenuItem(
            external_id=raw["guid"],
            name=raw["name"],
            description=raw.get("description", ""),
            price=Decimal(str(raw.get("price", 0))),
            image_url=raw.get("imageUrl", ""),
            is_available=raw.get("visibility") != "HIDDEN",
            modifier_groups=[
                self._parse_modifier_group(mg)
                for mg in raw.get("modifierGroups", [])
            ],
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        import hmac
        import hashlib

        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> POSWebhookEvent:
        event_type = payload.get("eventType", "")

        match event_type:
            case "ITEM_AVAILABILITY_CHANGED":
                return POSWebhookEvent(
                    event_type="item_availability_changed",
                    items=[
                        POSAvailabilityChange(
                            external_id=item["guid"],
                            is_available=item["visibility"] != "HIDDEN",
                        )
                        for item in payload.get("items", [])
                    ],
                )
            case "MENU_UPDATED":
                return POSWebhookEvent(
                    event_type="menu_updated",
                    menus=[m["guid"] for m in payload.get("menus", [])],
                )
            case _:
                return POSWebhookEvent(event_type="unknown", raw=payload)
```

### Rate Limiter

```python
# apps/web/pos/utils.py

import asyncio
from collections import deque
from datetime import datetime

class RateLimiter:
    def __init__(self, requests_per_second: float):
        self.min_interval = 1.0 / requests_per_second
        self.last_request: datetime | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            if self.last_request:
                elapsed = (datetime.now() - self.last_request).total_seconds()
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
            self.last_request = datetime.now()
```

### Error Handling

```python
class ToastAPIError(POSAPIError):
    """Toast-specific API error with error codes."""

    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(f"Toast API error {error_code}: {message}")
```

## Toast Partnership Notes

**Standard API Access** (read-only):
- Can fetch menus and item data
- Cannot create orders
- Sufficient for Phase 2

**Partner API Access** (full):
- Required for order creation (Phase 4)
- Requires formal partnership application
- May require revenue share agreement

**Action Item:** Begin Toast partnership application during Phase 2 development.

## Dependencies

- 008-A (POSAdapter protocol and types)
- Toast API credentials in Doppler

## Progress

### 2026-01-23: Implementation Complete

**Files created/modified:**
- `apps/web/pos/adapters/toast.py` - Full ToastAdapter implementation
- `apps/web/pos/adapters/__init__.py` - Added `get_adapter()` factory function
- `apps/web/pos/tests/test_toast_adapter.py` - 35 comprehensive tests
- `packages/schemas/consult_schemas/py.typed` - Added for mypy compatibility

**Implementation highlights:**
- Full `POSAdapter` protocol implementation with Toast API structure
- `RateLimiter` class for per-location request throttling (1 req/sec)
- HTTP retry logic with exponential backoff (3 attempts)
- Menu parsing with dietary flags extraction from Toast tags
- HMAC-SHA256 webhook signature verification
- Drop-in adapter registry: `get_adapter(POSProvider.TOAST)` or `get_adapter(POSProvider.MOCK)`

**Test coverage:**
- Authentication (success, invalid credentials, server error)
- Menu operations (menus, categories, items, modifiers, dietary flags, 86'd status)
- Error handling (rate limits, session expired, retries)
- Webhook parsing (menu_updated, item_availability_changed)
- Protocol compliance and adapter registry

**Note:** Order creation (`create_order`, `get_order_status`) raises `POSAPIError` - requires Toast Partner API access (Phase 4).
