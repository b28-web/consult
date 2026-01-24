"""Square POS adapter - integration with Square's commerce platform."""

import asyncio
import base64
import hashlib
import hmac
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    POSCredentials,
    POSMenu,
    POSMenuCategory,
    POSMenuItem,
    POSModifier,
    POSModifierGroup,
    POSOrder,
    POSOrderResult,
    POSOrderStatus,
    POSProvider,
    POSSession,
    POSWebhookEvent,
)

from apps.web.pos.exceptions import (
    POSAPIError,
    POSAuthError,
    POSRateLimitError,
    POSWebhookError,
)

logger = logging.getLogger(__name__)

# Square API version - update periodically
SQUARE_API_VERSION = "2024-01-18"


class SquareAdapter:
    """
    Square POS adapter implementing the POSAdapter protocol.

    Integrates with Square's commerce platform for:
    - Menu synchronization (via Catalog API)
    - Item availability (via Inventory API)
    - Webhook event handling

    Note: Square uses OAuth 2.0 with actual refresh tokens.
    Tokens expire and must be refreshed.

    API Reference: https://developer.squareup.com/reference/square
    """

    SANDBOX_BASE_URL = "https://connect.squareupsandbox.com"
    PROD_BASE_URL = "https://connect.squareup.com"

    # Square rate limits are per-endpoint, generally generous
    REQUESTS_PER_SECOND = 10.0

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0

    # Pagination limits
    CATALOG_PAGE_SIZE = 100
    INVENTORY_BATCH_SIZE = 100

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        sandbox: bool = False,
    ) -> None:
        """
        Initialize the Square adapter.

        Args:
            http_client: Optional HTTP client for dependency injection (testing).
            sandbox: If True, use Square sandbox environment.
        """
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._sandbox = sandbox
        self._base_url = self.SANDBOX_BASE_URL if sandbox else self.PROD_BASE_URL
        self._rate_limiter = _RateLimiter(self.REQUESTS_PER_SECOND)
        self._owns_client = http_client is None

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    @property
    def provider(self) -> POSProvider:
        """The POS provider this adapter connects to."""
        return POSProvider.SQUARE

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        """
        Exchange an authorization code for access and refresh tokens.

        Square uses OAuth 2.0 with proper refresh tokens:
        1. User authorizes via redirect to Square
        2. Square redirects back with an auth code
        3. Exchange auth code for tokens (this method)

        The auth_code should be provided in credentials.extra["auth_code"].

        Args:
            credentials: Square API credentials with auth_code.

        Returns:
            Authenticated session with access and refresh tokens.

        Raises:
            POSAuthError: If authentication fails.
        """
        auth_code = credentials.extra.get("auth_code")
        if not auth_code:
            raise POSAuthError(
                "Square authentication requires auth_code in credentials.extra",
                provider="square",
            )

        try:
            response = await self._client.post(
                f"{self._base_url}/oauth2/token",
                json={
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                },
            )

            if response.status_code == 401:
                raise POSAuthError(
                    "Invalid Square credentials or expired auth code",
                    provider="square",
                )

            response.raise_for_status()
            data = response.json()

            access_token = data.get("access_token")
            if not access_token:
                raise POSAuthError(
                    "No access token in Square response",
                    provider="square",
                )

            # Parse expiration time
            expires_at_str = data.get("expires_at", "")
            if expires_at_str:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
            else:
                # Default to 30 days if not specified
                expires_at = datetime.now(UTC) + timedelta(days=30)

            return POSSession(
                provider=POSProvider.SQUARE,
                access_token=access_token,
                refresh_token=data.get("refresh_token"),
                expires_at=expires_at,
            )

        except httpx.HTTPStatusError as e:
            raise POSAuthError(
                f"Square authentication failed: {e.response.status_code}",
                provider="square",
            ) from e
        except httpx.RequestError as e:
            raise POSAuthError(
                f"Square authentication request failed: {e}",
                provider="square",
            ) from e

    async def refresh_token(
        self, session: POSSession, credentials: POSCredentials | None = None
    ) -> POSSession:
        """
        Refresh an expired access token.

        Square tokens expire and must be refreshed using the refresh token.
        Note: refresh_token requires credentials for client_id/client_secret.

        Args:
            session: Current session with refresh token.
            credentials: Required - contains client_id and client_secret.

        Returns:
            New session with fresh access token.

        Raises:
            POSAuthError: If token refresh fails or credentials missing.
        """
        if not session.refresh_token:
            raise POSAuthError(
                "No refresh token available",
                provider="square",
            )

        if not credentials:
            raise POSAuthError(
                "Square token refresh requires credentials",
                provider="square",
            )

        try:
            response = await self._client.post(
                f"{self._base_url}/oauth2/token",
                json={
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "refresh_token": session.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 401:
                raise POSAuthError(
                    "Invalid refresh token or credentials",
                    provider="square",
                )

            response.raise_for_status()
            data = response.json()

            expires_at_str = data.get("expires_at", "")
            if expires_at_str:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
            else:
                expires_at = datetime.now(UTC) + timedelta(days=30)

            return POSSession(
                provider=POSProvider.SQUARE,
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", session.refresh_token),
                expires_at=expires_at,
            )

        except httpx.HTTPStatusError as e:
            raise POSAuthError(
                f"Square token refresh failed: {e.response.status_code}",
                provider="square",
            ) from e
        except httpx.RequestError as e:
            raise POSAuthError(
                f"Square token refresh request failed: {e}",
                provider="square",
            ) from e

    # =========================================================================
    # HTTP Helpers
    # =========================================================================

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        session: POSSession,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            session: Authenticated session
            **kwargs: Additional arguments passed to httpx

        Returns:
            HTTP response

        Raises:
            POSAPIError: If request fails after retries
            POSRateLimitError: If rate limit exceeded
        """
        headers = {
            "Authorization": f"Bearer {session.access_token}",
            "Square-Version": SQUARE_API_VERSION,
            "Content-Type": "application/json",
            **kwargs.pop("headers", {}),
        }

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            await self._rate_limiter.acquire()

            try:
                response = await self._client.request(
                    method, url, headers=headers, **kwargs
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise POSRateLimitError(
                        "Square rate limit exceeded",
                        provider="square",
                        retry_after=retry_after,
                    )

                if response.status_code == 401:
                    raise POSAuthError(
                        "Square session expired or invalid",
                        provider="square",
                    )

                response.raise_for_status()
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.RETRY_BACKOFF_BASE**attempt
                    logger.warning(
                        "Square API failed (attempt %d/%d), retry in %.1fs: %s",
                        attempt + 1,
                        self.MAX_RETRIES,
                        backoff,
                        str(e),
                    )
                    await asyncio.sleep(backoff)

        raise POSAPIError(
            f"Square API request failed after {self.MAX_RETRIES} attempts: "
            f"{last_error}",
            provider="square",
        )

    # =========================================================================
    # Menu Operations
    # =========================================================================

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        """
        Get all menus for a Square location.

        Square uses a flat catalog structure:
        - Categories (similar to menu sections)
        - Items (belong to categories, have variations with prices)
        - Modifier lists (optional add-ons)

        We model this as a single "Menu" containing all categories.

        Args:
            session: Authenticated session.
            location_id: Square location ID.

        Returns:
            List containing one menu with all categories and items.

        Raises:
            POSAPIError: If the API request fails.
        """
        catalog = await self._fetch_catalog(session)

        # Build lookup maps from catalog
        categories, items, modifier_lists = self._parse_catalog_objects(catalog)

        # Group items by category
        items_by_category, uncategorized = self._group_items_by_category(items)

        # Build menu categories
        pos_categories = self._build_pos_categories(
            categories, items_by_category, uncategorized, location_id, modifier_lists
        )

        return [
            POSMenu(
                external_id="main",
                name="Menu",
                description="",
                categories=pos_categories,
            )
        ]

    def _parse_catalog_objects(
        self, catalog: list[dict[str, Any]]
    ) -> tuple[
        dict[str, dict[str, Any]],
        list[dict[str, Any]],
        dict[str, dict[str, Any]],
    ]:
        """Parse catalog into categories, items, and modifier lists."""
        categories: dict[str, dict[str, Any]] = {}
        items: list[dict[str, Any]] = []
        modifier_lists: dict[str, dict[str, Any]] = {}

        for obj in catalog:
            obj_type = obj.get("type", "")
            if obj_type == "CATEGORY":
                categories[obj["id"]] = obj.get("category_data", {})
            elif obj_type == "ITEM":
                items.append(obj)
            elif obj_type == "MODIFIER_LIST":
                modifier_lists[obj["id"]] = obj.get("modifier_list_data", {})

        return categories, items, modifier_lists

    def _group_items_by_category(
        self, items: list[dict[str, Any]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
        """Group items by their category ID."""
        items_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        uncategorized: list[dict[str, Any]] = []

        for item in items:
            item_data = item.get("item_data", {})
            cat_id = item_data.get("category_id")

            if cat_id:
                items_by_category[cat_id].append(item)
            else:
                # Check for categories list (newer API)
                cat_refs = item_data.get("categories", [])
                if cat_refs:
                    for cat_ref in cat_refs:
                        items_by_category[cat_ref.get("id", "")].append(item)
                else:
                    uncategorized.append(item)

        return items_by_category, uncategorized

    def _build_pos_categories(
        self,
        categories: dict[str, dict[str, Any]],
        items_by_category: dict[str, list[dict[str, Any]]],
        uncategorized: list[dict[str, Any]],
        location_id: str,
        modifier_lists: dict[str, dict[str, Any]],
    ) -> list[POSMenuCategory]:
        """Build POS menu categories from parsed catalog data."""
        pos_categories: list[POSMenuCategory] = []

        for cat_id, cat_data in categories.items():
            cat_items = items_by_category.get(cat_id, [])
            if cat_items:
                pos_categories.append(
                    POSMenuCategory(
                        external_id=cat_id,
                        name=cat_data.get("name", ""),
                        description="",
                        items=[
                            self._parse_item(i, location_id, modifier_lists)
                            for i in cat_items
                        ],
                    )
                )

        if uncategorized:
            pos_categories.append(
                POSMenuCategory(
                    external_id="uncategorized",
                    name="Other Items",
                    items=[
                        self._parse_item(i, location_id, modifier_lists)
                        for i in uncategorized
                    ],
                )
            )

        return pos_categories

    async def get_menu(
        self, session: POSSession, location_id: str, menu_id: str
    ) -> POSMenu:
        """
        Get a specific menu by ID.

        Since Square only has one conceptual "menu", this returns the same
        result as get_menus() for the main menu.

        Args:
            session: Authenticated session.
            location_id: Square location ID.
            menu_id: Menu identifier (only "main" is supported).

        Returns:
            The requested menu.

        Raises:
            POSAPIError: If menu_id is not "main".
        """
        if menu_id != "main":
            raise POSAPIError(
                f"Menu not found: {menu_id}. Square only supports 'main' menu.",
                provider="square",
                status_code=404,
            )

        menus = await self.get_menus(session, location_id)
        return menus[0]

    async def get_item_availability(
        self, session: POSSession, location_id: str
    ) -> dict[str, bool]:
        """
        Get current availability status for all items.

        Square tracks inventory at the variation level. An item is available
        if any of its variations are in stock.

        Args:
            session: Authenticated session.
            location_id: Square location ID.

        Returns:
            Dict mapping item ID to availability (True = available).

        Raises:
            POSAPIError: If the API request fails.
        """
        # First get all item variation IDs from catalog
        catalog = await self._fetch_catalog(session)

        # Map variation IDs to their parent item IDs
        variation_to_item: dict[str, str] = {}
        for obj in catalog:
            if obj.get("type") == "ITEM":
                item_id = obj["id"]
                item_data = obj.get("item_data", {})
                for var in item_data.get("variations", []):
                    variation_to_item[var["id"]] = item_id

        if not variation_to_item:
            return {}

        # Batch retrieve inventory counts
        variation_ids = list(variation_to_item.keys())
        all_counts: list[dict[str, Any]] = []

        # Square limits batch size
        for i in range(0, len(variation_ids), self.INVENTORY_BATCH_SIZE):
            batch = variation_ids[i : i + self.INVENTORY_BATCH_SIZE]
            response = await self._request_with_retry(
                "POST",
                f"{self._base_url}/v2/inventory/counts/batch-retrieve",
                session,
                json={
                    "catalog_object_ids": batch,
                    "location_ids": [location_id],
                },
            )
            data = response.json()
            all_counts.extend(data.get("counts", []))

        # Build availability map at item level
        # Item is available if ANY variation is in stock
        # Track which items have inventory records vs no tracking
        items_with_inventory: set[str] = set()
        item_has_stock: dict[str, bool] = {}

        for count in all_counts:
            var_id = count.get("catalog_object_id", "")
            item_id = variation_to_item.get(var_id, "")
            if not item_id:
                continue

            items_with_inventory.add(item_id)

            # Check if this variation is in stock
            state = count.get("state", "")
            quantity = count.get("quantity", "0")
            try:
                qty = float(quantity)
            except (ValueError, TypeError):
                qty = 0

            is_in_stock = state == "IN_STOCK" or qty > 0
            if is_in_stock:
                item_has_stock[item_id] = True

        # Return availability for all items
        # Items with inventory tracking: use tracked status (default False)
        # Items without inventory tracking: assume available (True)
        availability: dict[str, bool] = {}
        for item_id in set(variation_to_item.values()):
            if item_id in items_with_inventory:
                availability[item_id] = item_has_stock.get(item_id, False)
            else:
                availability[item_id] = True  # No tracking = available

        return availability

    async def _fetch_catalog(self, session: POSSession) -> list[dict[str, Any]]:
        """Fetch full catalog with pagination."""
        all_objects: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            body: dict[str, Any] = {
                "object_types": ["ITEM", "CATEGORY", "MODIFIER_LIST"],
                "include_related_objects": True,
            }
            if cursor:
                body["cursor"] = cursor

            response = await self._request_with_retry(
                "POST",
                f"{self._base_url}/v2/catalog/search",
                session,
                json=body,
            )
            data: dict[str, Any] = response.json()

            objects: list[dict[str, Any]] = data.get("objects", [])
            related: list[dict[str, Any]] = data.get("related_objects", [])
            all_objects.extend(objects)
            all_objects.extend(related)

            cursor = data.get("cursor")
            if not cursor:
                break

        return all_objects

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def _parse_item(
        self,
        raw: dict[str, Any],
        location_id: str,
        modifier_lists: dict[str, dict[str, Any]],
    ) -> POSMenuItem:
        """Convert Square catalog item to internal POSMenuItem."""
        item_data = raw.get("item_data", {})

        # Get price from first variation (Square items have multiple variations)
        price = Decimal("0")
        for var in item_data.get("variations", []):
            var_data = var.get("item_variation_data", {})

            # Check for location-specific pricing
            location_overrides = var_data.get("location_overrides", [])
            for override in location_overrides:
                if override.get("location_id") == location_id:
                    price_money = override.get("price_money", {})
                    if price_money:
                        price = Decimal(price_money.get("amount", 0)) / 100
                        break

            # Fall back to default price
            if price == 0:
                price_money = var_data.get("price_money", {})
                if price_money:
                    price = Decimal(price_money.get("amount", 0)) / 100

            if price > 0:
                break  # Use first variation with a price

        # Parse modifier groups
        modifier_groups: list[POSModifierGroup] = []
        for mod_info in item_data.get("modifier_list_info", []):
            mod_list_id = mod_info.get("modifier_list_id", "")
            if mod_list_id in modifier_lists:
                modifier_groups.append(
                    self._parse_modifier_group(
                        mod_list_id, modifier_lists[mod_list_id], mod_info
                    )
                )

        # Note: Would need separate API call to get actual image URL
        # Square images are stored separately - for now leave empty
        image_url = ""

        return POSMenuItem(
            external_id=raw["id"],
            name=item_data.get("name", ""),
            description=item_data.get("description", ""),
            price=price,
            image_url=image_url,
            is_available=True,  # Will be updated by availability check
            modifier_groups=modifier_groups,
            # Square doesn't have built-in dietary flags
            is_vegetarian=False,
            is_vegan=False,
            is_gluten_free=False,
            allergens=[],
        )

    def _parse_modifier_group(
        self,
        mod_list_id: str,
        mod_list_data: dict[str, Any],
        mod_info: dict[str, Any],
    ) -> POSModifierGroup:
        """Convert Square modifier list to internal format."""
        modifiers: list[POSModifier] = []
        for mod in mod_list_data.get("modifiers", []):
            mod_data = mod.get("modifier_data", {})
            price_money = mod_data.get("price_money", {})
            price_adjustment = Decimal(price_money.get("amount", 0)) / 100

            modifiers.append(
                POSModifier(
                    external_id=mod.get("id", ""),
                    name=mod_data.get("name", ""),
                    price_adjustment=price_adjustment,
                    is_available=True,  # Square doesn't track modifier availability
                )
            )

        # Get selection requirements from mod_info
        min_selected = mod_info.get("min_selected_modifiers", 0)
        max_selected = mod_info.get("max_selected_modifiers", len(modifiers))

        return POSModifierGroup(
            external_id=mod_list_id,
            name=mod_list_data.get("name", ""),
            min_selections=min_selected or 0,
            max_selections=max_selected or 1,
            modifiers=modifiers,
        )

    # =========================================================================
    # Order Operations (Phase 4 - Not Implemented)
    # =========================================================================

    async def create_order(
        self,
        session: POSSession,  # noqa: ARG002
        location_id: str,  # noqa: ARG002
        order: POSOrder,  # noqa: ARG002
    ) -> POSOrderResult:
        """
        Create a new order in Square.

        Note: Will be implemented in Phase 4 using Square Orders API.

        Raises:
            POSAPIError: Always - not implemented yet.
        """
        raise POSAPIError(
            "Order creation will be implemented in Phase 4",
            provider="square",
        )

    async def get_order_status(
        self,
        session: POSSession,  # noqa: ARG002
        location_id: str,  # noqa: ARG002
        order_id: str,  # noqa: ARG002
    ) -> POSOrderStatus:
        """
        Get current status of an order.

        Note: Will be implemented in Phase 4.

        Raises:
            POSAPIError: Always - not implemented yet.
        """
        raise POSAPIError(
            "Order status will be implemented in Phase 4",
            provider="square",
        )

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        notification_url: str | None = None,
    ) -> bool:
        """
        Verify Square webhook signature.

        Square uses HMAC-SHA256 with the notification URL + body.
        Signature is base64-encoded and sent in x-square-hmacsha256-signature.

        Args:
            payload: Raw webhook payload bytes.
            signature: Value from x-square-hmacsha256-signature header.
            secret: Webhook signature key from Square dashboard.
            notification_url: The webhook endpoint URL (required for signature).

        Returns:
            True if signature is valid.
        """
        if not notification_url:
            # Without URL, can't verify - log warning and accept
            logger.warning("Square webhook verification called without URL")
            return True

        # Square signature is: HMAC-SHA256(webhook_signature_key, url + body)
        combined = notification_url.encode() + payload
        expected = base64.b64encode(
            hmac.new(secret.encode(), combined, hashlib.sha256).digest()
        ).decode()

        return hmac.compare_digest(signature, expected)

    def parse_webhook(self, payload: dict[str, Any]) -> POSWebhookEvent:
        """
        Parse a Square webhook payload into a typed event.

        Square webhook event types:
        - inventory.count.updated: Stock level changed
        - catalog.version.updated: Catalog changed

        Args:
            payload: Parsed JSON webhook payload.

        Returns:
            Typed webhook event.

        Raises:
            POSWebhookError: If payload cannot be parsed.
        """
        event_type = payload.get("type", "")
        event_id = payload.get("event_id", "")

        # Parse timestamp
        created_at = payload.get("created_at", "")
        try:
            if created_at:
                occurred_at = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            else:
                occurred_at = datetime.now(UTC)
        except ValueError as e:
            raise POSWebhookError(
                f"Invalid timestamp in Square webhook: {e}",
                provider="square",
            ) from e

        if event_type == "inventory.count.updated":
            data = payload.get("data", {}).get("object", {})
            inventory_counts = data.get("inventory_counts", [])

            if not inventory_counts:
                raise POSWebhookError(
                    "No inventory counts in Square webhook",
                    provider="square",
                )

            count = inventory_counts[0]
            catalog_object_id = count.get("catalog_object_id", "")
            state = count.get("state", "")
            quantity = count.get("quantity", "0")

            try:
                qty = float(quantity)
            except (ValueError, TypeError):
                qty = 0

            is_available = state == "IN_STOCK" or qty > 0

            return ItemAvailabilityChangedEvent(
                provider=POSProvider.SQUARE,
                event_id=event_id,
                occurred_at=occurred_at,
                item_id=catalog_object_id,
                is_available=is_available,
            )

        elif event_type == "catalog.version.updated":
            return MenuUpdatedEvent(
                provider=POSProvider.SQUARE,
                event_id=event_id,
                occurred_at=occurred_at,
                menu_id="main",
            )

        else:
            raise POSWebhookError(
                f"Unknown Square webhook event type: {event_type}",
                provider="square",
            )


class _RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float = 10.0) -> None:
        self.min_interval = 1.0 / requests_per_second
        self.last_request: datetime | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request can be made within rate limits."""
        async with self._lock:
            if self.last_request:
                elapsed = (datetime.now(UTC) - self.last_request).total_seconds()
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
            self.last_request = datetime.now(UTC)
