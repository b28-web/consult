# 008-H: Square Adapter Implementation

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 3 (Additional POS Providers)

## Summary

Implement the Square POS adapter following the `POSAdapter` protocol. Square uses the Catalog API for menu data and the Inventory API for stock levels. Square has excellent documentation and a robust sandbox.

## Acceptance Criteria

- [x] `SquareAdapter` class implementing `POSAdapter` protocol
- [x] OAuth 2.0 authentication
- [x] Token refresh handling
- [x] `get_menus()` - Fetch catalog items and categories
- [x] `get_menu()` - Fetch filtered catalog by category
- [x] `get_item_availability()` - Fetch inventory counts
- [x] `verify_webhook_signature()` - Square signature validation (URL + body)
- [x] `parse_webhook()` - Convert Square events to internal format
- [x] `create_order()` - Create order via Orders API (stub for Phase 4)
- [x] Sandbox vs production environment handling
- [x] Pagination handling for large catalogs
- [x] Unit tests with mocked HTTP responses
- [ ] Integration test with Square sandbox (deferred - requires Square developer account)

## Implementation Notes

### Square API Reference

**OAuth Flow:**
```
1. Redirect to authorization:
   GET https://connect.squareup.com/oauth2/authorize
     ?client_id={{appId}}
     &scope=ITEMS_READ INVENTORY_READ ORDERS_WRITE
     &redirect_uri={{redirectUri}}

2. Exchange code for token:
   POST https://connect.squareup.com/oauth2/token
   {
     "client_id": "{{appId}}",
     "client_secret": "{{appSecret}}",
     "code": "{{authCode}}",
     "grant_type": "authorization_code"
   }

   Response:
   {
     "access_token": "...",
     "refresh_token": "...",
     "expires_at": "2026-02-21T12:00:00Z",
     "merchant_id": "..."
   }
```

**Catalog API:**
```
POST https://connect.squareup.com/v2/catalog/search
{
  "object_types": ["ITEM", "CATEGORY", "MODIFIER_LIST"],
  "include_related_objects": true
}
```

**Inventory API:**
```
POST https://connect.squareup.com/v2/inventory/counts/batch-retrieve
{
  "catalog_object_ids": ["item_id_1", "item_id_2"],
  "location_ids": ["location_id"]
}
```

**Webhooks:**
- Signature header: `x-square-hmacsha256-signature`
- Events: `inventory.count.updated`, `catalog.version.updated`

### Adapter Implementation

```python
# apps/web/pos/adapters/square.py

class SquareAdapter:
    provider = "square"

    SANDBOX_BASE = "https://connect.squareupsandbox.com"
    PROD_BASE = "https://connect.squareup.com"

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        sandbox: bool = False,
    ):
        self._client = http_client or httpx.AsyncClient()
        self._base_url = self.SANDBOX_BASE if sandbox else self.PROD_BASE

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        response = await self._client.post(
            f"{self._base_url}/oauth2/token",
            json={
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "code": credentials.extras.get("auth_code"),
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

        return POSSession(
            provider=self.provider,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            extras={"merchant_id": data.get("merchant_id")},
        )

    async def refresh_token(self, session: POSSession, credentials: POSCredentials) -> POSSession:
        response = await self._client.post(
            f"{self._base_url}/oauth2/token",
            json={
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "refresh_token": session.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

        return POSSession(
            provider=self.provider,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            extras=session.extras,
        )

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        catalog = await self._fetch_catalog(session)

        # Build lookup maps
        categories = {
            obj["id"]: obj["category_data"]
            for obj in catalog
            if obj["type"] == "CATEGORY"
        }
        items = [obj for obj in catalog if obj["type"] == "ITEM"]

        # Group items by category
        items_by_category = defaultdict(list)
        for item in items:
            item_data = item["item_data"]
            for cat_id in item_data.get("category_ids", []):
                items_by_category[cat_id].append(item)

        # Build menu structure
        return [
            POSMenu(
                external_id="main",
                name="Menu",
                categories=[
                    POSMenuCategory(
                        external_id=cat_id,
                        name=cat_data["name"],
                        items=[
                            self._parse_item(i, location_id)
                            for i in items_by_category[cat_id]
                        ],
                    )
                    for cat_id, cat_data in categories.items()
                ],
            )
        ]

    async def _fetch_catalog(self, session: POSSession) -> list[dict]:
        """Fetch full catalog with pagination."""
        all_objects = []
        cursor = None

        while True:
            body = {
                "object_types": ["ITEM", "CATEGORY", "MODIFIER_LIST"],
                "include_related_objects": True,
            }
            if cursor:
                body["cursor"] = cursor

            response = await self._client.post(
                f"{self._base_url}/v2/catalog/search",
                headers={
                    "Authorization": f"Bearer {session.access_token}",
                    "Square-Version": "2024-01-18",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            all_objects.extend(data.get("objects", []))
            all_objects.extend(data.get("related_objects", []))

            cursor = data.get("cursor")
            if not cursor:
                break

        return all_objects

    async def get_item_availability(
        self,
        session: POSSession,
        location_id: str,
    ) -> dict[str, bool]:
        """Fetch inventory counts for location."""
        # First, get all item variation IDs
        catalog = await self._fetch_catalog(session)
        variation_ids = []
        for obj in catalog:
            if obj["type"] == "ITEM":
                for var in obj["item_data"].get("variations", []):
                    variation_ids.append(var["id"])

        if not variation_ids:
            return {}

        # Batch retrieve inventory counts
        response = await self._client.post(
            f"{self._base_url}/v2/inventory/counts/batch-retrieve",
            headers={
                "Authorization": f"Bearer {session.access_token}",
                "Square-Version": "2024-01-18",
            },
            json={
                "catalog_object_ids": variation_ids,
                "location_ids": [location_id],
            },
        )
        response.raise_for_status()
        data = response.json()

        # Map variation ID to availability
        availability = {}
        for count in data.get("counts", []):
            # Quantity > 0 or state is IN_STOCK means available
            is_available = (
                count.get("state") == "IN_STOCK"
                or float(count.get("quantity", "0")) > 0
            )
            availability[count["catalog_object_id"]] = is_available

        return availability

    def _parse_item(self, raw: dict, location_id: str) -> POSMenuItem:
        item_data = raw["item_data"]

        # Get price from first variation at this location
        price = Decimal("0")
        for var in item_data.get("variations", []):
            var_data = var.get("item_variation_data", {})
            price_money = var_data.get("price_money", {})
            if price_money:
                price = Decimal(price_money.get("amount", 0)) / 100
                break

        return POSMenuItem(
            external_id=raw["id"],
            name=item_data["name"],
            description=item_data.get("description", ""),
            price=price,
            image_url=item_data.get("image_url", ""),
            is_available=True,  # Updated via availability fetch
            modifier_groups=[
                self._parse_modifier_group(mg_id)
                for mg_id in item_data.get("modifier_list_info", [])
            ],
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        url: str,
    ) -> bool:
        """Square uses URL + body for signature."""
        import hmac
        import hashlib
        import base64

        combined = url.encode() + payload
        expected = base64.b64encode(
            hmac.new(secret.encode(), combined, hashlib.sha256).digest()
        ).decode()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> POSWebhookEvent:
        event_type = payload.get("type", "")

        match event_type:
            case "inventory.count.updated":
                data = payload["data"]["object"]["inventory_count"]
                return POSWebhookEvent(
                    event_type="item_availability_changed",
                    items=[
                        POSAvailabilityChange(
                            external_id=data["catalog_object_id"],
                            is_available=(
                                data.get("state") == "IN_STOCK"
                                or float(data.get("quantity", "0")) > 0
                            ),
                        )
                    ],
                )
            case "catalog.version.updated":
                return POSWebhookEvent(
                    event_type="menu_updated",
                    menus=["main"],  # Square doesn't have named menus
                )
            case _:
                return POSWebhookEvent(event_type="unknown", raw=payload)
```

### Square SDK Option

Square provides an official Python SDK that could simplify implementation:

```python
from square.client import Client

client = Client(
    access_token=session.access_token,
    environment="sandbox",  # or "production"
)

result = client.catalog.search_catalog_objects(
    body={"object_types": ["ITEM", "CATEGORY"]}
)
```

**Decision:** Implement with raw httpx first for consistency with other adapters. Consider SDK migration if maintenance becomes difficult.

### Key Differences from Toast/Clover

| Aspect | Toast | Clover | Square |
|--------|-------|--------|--------|
| Menu structure | Menus → Groups → Items | Categories → Items | Categories → Items |
| Item variants | Single price | Single price | Multiple variations |
| Prices | Dollars | Cents | Cents |
| Inventory | Visibility flag | Stock quantity | Stock count + state |
| Webhook signature | Body only | Body only | URL + Body |

## Dependencies

- 008-A (POSAdapter protocol and types)
- 008-F, 008-G (Reference implementations for consistency)
- Square developer account for sandbox testing

## Progress

### 2026-01-23
- **Complete**: Full SquareAdapter implementation in `apps/web/pos/adapters/square.py`
  - OAuth 2.0 authentication with actual token refresh support
  - Catalog API with pagination handling
  - `get_menus()` parses categories, items, and modifier lists
  - `get_item_availability()` via batch inventory API with correct out-of-stock detection
  - `verify_webhook_signature()` using URL + body (Square's unique signature scheme)
  - `parse_webhook()` handles inventory.count.updated and catalog.version.updated
  - Order operations stubbed for Phase 4
  - Environment switching (sandbox/production)
  - Rate limiting (10 req/sec) with retry logic (3 attempts with exponential backoff)
- **Tests**: 39 unit tests in `apps/web/pos/tests/test_square_adapter.py`
  - Authentication (7 tests - including token refresh)
  - Menu operations (10 tests - including pagination)
  - Error handling (4 tests)
  - Webhooks (7 tests)
  - Order operations (2 tests)
  - Protocol compliance (2 tests)
  - Adapter registry (3 tests)
  - Environment switching (3 tests)
- **Registry**: Updated `apps/web/pos/adapters/__init__.py` to include SquareAdapter
- All quality checks pass (ruff, mypy, 139 adapter tests)
