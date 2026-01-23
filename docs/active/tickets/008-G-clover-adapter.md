# 008-G: Clover Adapter Implementation

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 3 (Additional POS Providers)

## Summary

Implement the Clover POS adapter following the `POSAdapter` protocol. Clover uses OAuth 2.0 with merchant authorization flow and has a developer-friendly sandbox environment.

## Acceptance Criteria

- [x] `CloverAdapter` class implementing `POSAdapter` protocol
- [x] OAuth 2.0 merchant authorization flow
- [x] Token refresh handling
- [x] `get_menus()` - Fetch categories and items
- [x] `get_menu()` - Fetch single category with items
- [x] `get_item_availability()` - Fetch inventory stock status
- [x] `verify_webhook_signature()` - Clover webhook validation
- [x] `parse_webhook()` - Convert Clover events to internal format
- [x] `create_order()` - Create order in Clover (stub for Phase 4)
- [x] Environment switching (sandbox vs production)
- [x] Unit tests with mocked HTTP responses
- [ ] Integration test with Clover sandbox (deferred - requires Clover developer account)

## Implementation Notes

### Clover API Reference

**OAuth Flow:**
```
1. Redirect merchant to authorization:
   GET https://sandbox.dev.clover.com/oauth/authorize
     ?client_id={{appId}}
     &redirect_uri={{redirectUri}}

2. Exchange code for token:
   POST https://sandbox.dev.clover.com/oauth/token
   {
     "client_id": "{{appId}}",
     "client_secret": "{{appSecret}}",
     "code": "{{authCode}}"
   }

   Response:
   {
     "access_token": "...",
     "merchant_id": "..."
   }
```

**Inventory/Items Endpoints:**
```
GET https://api.clover.com/v3/merchants/{mId}/items
GET https://api.clover.com/v3/merchants/{mId}/categories
GET https://api.clover.com/v3/merchants/{mId}/item_stocks
```

**Webhooks:**
- Events: `inventory.updated`, `items.updated`, `orders.created`
- Verification: Clover-specific signature header

### Adapter Implementation

```python
# apps/web/pos/adapters/clover.py

class CloverAdapter:
    provider = "clover"

    SANDBOX_BASE = "https://sandbox.dev.clover.com"
    PROD_BASE = "https://api.clover.com"

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        sandbox: bool = False,
    ):
        self._client = http_client or httpx.AsyncClient()
        self._base_url = self.SANDBOX_BASE if sandbox else self.PROD_BASE

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        """
        Note: Clover uses merchant authorization flow.
        This method exchanges an auth code for access token.
        Initial auth code must be obtained via redirect flow.
        """
        response = await self._client.post(
            f"{self._base_url}/oauth/token",
            json={
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "code": credentials.extras.get("auth_code"),
            },
        )
        response.raise_for_status()
        data = response.json()

        return POSSession(
            provider=self.provider,
            access_token=data["access_token"],
            refresh_token=None,  # Clover tokens don't expire
            expires_at=None,
            extras={"merchant_id": data.get("merchant_id")},
        )

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        """Clover doesn't have "menus" - we treat categories as menu sections."""
        categories = await self._fetch_categories(session, location_id)
        items = await self._fetch_items(session, location_id)

        # Group items by category
        items_by_category = defaultdict(list)
        for item in items:
            for cat in item.get("categories", {}).get("elements", []):
                items_by_category[cat["id"]].append(item)

        # Build single "menu" from categories
        return [
            POSMenu(
                external_id="main",
                name="Menu",
                categories=[
                    POSMenuCategory(
                        external_id=cat["id"],
                        name=cat["name"],
                        items=[
                            self._parse_item(i) for i in items_by_category[cat["id"]]
                        ],
                    )
                    for cat in categories
                ],
            )
        ]

    async def _fetch_categories(self, session: POSSession, merchant_id: str) -> list:
        response = await self._client.get(
            f"{self._base_url}/v3/merchants/{merchant_id}/categories",
            headers={"Authorization": f"Bearer {session.access_token}"},
        )
        response.raise_for_status()
        return response.json().get("elements", [])

    async def _fetch_items(self, session: POSSession, merchant_id: str) -> list:
        response = await self._client.get(
            f"{self._base_url}/v3/merchants/{merchant_id}/items",
            headers={"Authorization": f"Bearer {session.access_token}"},
            params={"expand": "categories,modifierGroups"},
        )
        response.raise_for_status()
        return response.json().get("elements", [])

    async def get_item_availability(
        self,
        session: POSSession,
        location_id: str,
    ) -> dict[str, bool]:
        """Fetch stock status for all items."""
        response = await self._client.get(
            f"{self._base_url}/v3/merchants/{location_id}/item_stocks",
            headers={"Authorization": f"Bearer {session.access_token}"},
        )
        response.raise_for_status()

        stocks = response.json().get("elements", [])
        return {
            stock["item"]["id"]: stock.get("quantity", 0) > 0
            for stock in stocks
        }

    def _parse_item(self, raw: dict) -> POSMenuItem:
        return POSMenuItem(
            external_id=raw["id"],
            name=raw["name"],
            description=raw.get("description", ""),
            price=Decimal(raw.get("price", 0)) / 100,  # Clover uses cents
            image_url=raw.get("imageUrl", ""),
            is_available=not raw.get("hidden", False),
            modifier_groups=[
                self._parse_modifier_group(mg)
                for mg in raw.get("modifierGroups", {}).get("elements", [])
            ],
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        # Clover webhook verification logic
        # (implementation depends on Clover's specific signature format)
        import hmac
        import hashlib

        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> POSWebhookEvent:
        event_type = payload.get("type", "")

        match event_type:
            case "inventory.updated":
                return POSWebhookEvent(
                    event_type="item_availability_changed",
                    items=[
                        POSAvailabilityChange(
                            external_id=payload["data"]["item"]["id"],
                            is_available=payload["data"]["quantity"] > 0,
                        )
                    ],
                )
            case "items.updated":
                return POSWebhookEvent(
                    event_type="item_updated",
                    items=[
                        POSItemUpdate(
                            external_id=payload["data"]["id"],
                            changes=payload["data"],
                        )
                    ],
                )
            case _:
                return POSWebhookEvent(event_type="unknown", raw=payload)
```

### Clover Sandbox

Clover has a developer-friendly sandbox:
- Create test merchants at https://sandbox.dev.clover.com/developers
- Test API calls without real merchant accounts
- Webhook testing via ngrok or similar

### Differences from Toast

| Aspect | Toast | Clover |
|--------|-------|--------|
| Auth | Client credentials | Merchant authorization |
| Menu structure | Menus → Groups → Items | Categories → Items |
| Prices | Dollars | Cents |
| Token expiry | 24 hours | No expiry |
| Webhooks | Push to configured URL | Push to configured URL |

## Dependencies

- 008-A (POSAdapter protocol and types)
- 008-F (Reference Toast implementation for consistency)
- Clover developer account for sandbox testing

## Progress

### 2026-01-23
- **Complete**: Full CloverAdapter implementation in `apps/web/pos/adapters/clover.py`
  - OAuth 2.0 merchant authorization flow (auth code exchange)
  - Token refresh returns same session (Clover tokens don't expire)
  - `get_menus()` fetches categories and items in parallel, groups by category
  - `get_menu()` supports single "main" menu concept (Clover has no menu hierarchy)
  - `get_item_availability()` via item_stocks endpoint with stock tracking detection
  - `verify_webhook_signature()` with HMAC-SHA256
  - `parse_webhook()` handles ITEM, CATEGORY, and inventory (I) events
  - Order operations stubbed for Phase 4
  - Environment switching (sandbox/production)
  - Rate limiting (10 req/sec) with retry logic (3 attempts with exponential backoff)
- **Tests**: 38 unit tests in `apps/web/pos/tests/test_clover_adapter.py`
  - Authentication (5 tests)
  - Menu operations (10 tests)
  - Error handling (4 tests)
  - Webhooks (9 tests)
  - Order operations (2 tests)
  - Protocol compliance (2 tests)
  - Adapter registry (3 tests)
  - Environment switching (3 tests)
- **Registry**: Updated `apps/web/pos/adapters/__init__.py` to include CloverAdapter
- All quality checks pass (ruff, mypy, 100 adapter tests)
