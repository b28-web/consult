"""Clover POS adapter - integration with Clover's merchant platform."""

import asyncio
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


class CloverAdapter:
    """
    Clover POS adapter implementing the POSAdapter protocol.

    Integrates with Clover's merchant platform for:
    - Menu synchronization (categories → items)
    - Item availability (stock tracking)
    - Webhook event handling

    Note: Clover uses OAuth 2.0 with merchant authorization flow.
    Unlike Toast, Clover tokens don't expire.

    API Reference: https://docs.clover.com/reference
    """

    SANDBOX_BASE_URL = "https://sandbox.dev.clover.com"
    PROD_BASE_URL = "https://api.clover.com"

    # Clover rate limits vary by endpoint, but generally more lenient than Toast
    REQUESTS_PER_SECOND = 10.0

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        sandbox: bool = False,
    ) -> None:
        """
        Initialize the Clover adapter.

        Args:
            http_client: Optional HTTP client for dependency injection (testing).
            sandbox: If True, use Clover sandbox environment.
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
        return POSProvider.CLOVER

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        """
        Exchange an authorization code for an access token.

        Clover uses OAuth 2.0 merchant authorization flow:
        1. Merchant authorizes via redirect to Clover
        2. Clover redirects back with an auth code
        3. Exchange auth code for access token (this method)

        The auth_code should be provided in credentials.extra["auth_code"].

        Args:
            credentials: Clover API credentials with auth_code.

        Returns:
            Authenticated session with access token.

        Raises:
            POSAuthError: If authentication fails.
        """
        auth_code = credentials.extra.get("auth_code")
        if not auth_code:
            raise POSAuthError(
                "Clover authentication requires auth_code in credentials.extra",
                provider="clover",
            )

        try:
            response = await self._client.post(
                f"{self._base_url}/oauth/token",
                json={
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "code": auth_code,
                },
            )

            if response.status_code == 401:
                raise POSAuthError(
                    "Invalid Clover credentials or expired auth code",
                    provider="clover",
                )

            response.raise_for_status()
            data = response.json()

            access_token = data.get("access_token")
            if not access_token:
                raise POSAuthError(
                    "No access token in Clover response",
                    provider="clover",
                )

            # Clover tokens don't expire, but we set a far-future expiry
            # to satisfy the POSSession contract
            return POSSession(
                provider=POSProvider.CLOVER,
                access_token=access_token,
                refresh_token=None,  # Clover doesn't use refresh tokens
                expires_at=datetime.now(UTC) + timedelta(days=365 * 10),
            )

        except httpx.HTTPStatusError as e:
            raise POSAuthError(
                f"Clover authentication failed: {e.response.status_code}",
                provider="clover",
            ) from e
        except httpx.RequestError as e:
            raise POSAuthError(
                f"Clover authentication request failed: {e}",
                provider="clover",
            ) from e

    async def refresh_token(self, session: POSSession) -> POSSession:
        """
        Refresh an expired access token.

        Clover tokens don't expire - this method exists for protocol
        compatibility. The original token can be reused indefinitely.

        Args:
            session: Current session.

        Returns:
            Same session (token doesn't expire).
        """
        # Clover tokens don't expire, so we just return the same session
        return session

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
                        "Clover rate limit exceeded",
                        provider="clover",
                        retry_after=retry_after,
                    )

                if response.status_code == 401:
                    raise POSAuthError(
                        "Clover session invalid",
                        provider="clover",
                    )

                response.raise_for_status()
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.RETRY_BACKOFF_BASE**attempt
                    logger.warning(
                        "Clover API failed (attempt %d/%d), retry in %.1fs: %s",
                        attempt + 1,
                        self.MAX_RETRIES,
                        backoff,
                        str(e),
                    )
                    await asyncio.sleep(backoff)

        raise POSAPIError(
            f"Clover API request failed after {self.MAX_RETRIES} attempts: "
            f"{last_error}",
            provider="clover",
        )

    # =========================================================================
    # Menu Operations
    # =========================================================================

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        """
        Get all menus for a Clover merchant.

        Clover doesn't have a "menu" concept like Toast. Instead, it has:
        - Categories (similar to menu groups)
        - Items (belong to one or more categories)

        We model this as a single "Menu" containing all categories.

        Args:
            session: Authenticated session.
            location_id: Clover merchant ID.

        Returns:
            List containing one menu with all categories and items.

        Raises:
            POSAPIError: If the API request fails.
        """
        # Fetch categories and items in parallel
        categories_task = self._fetch_categories(session, location_id)
        items_task = self._fetch_items(session, location_id)

        categories_raw, items_raw = await asyncio.gather(categories_task, items_task)

        # Group items by category
        items_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        uncategorized_items: list[dict[str, Any]] = []

        for item in items_raw:
            item_categories = item.get("categories", {}).get("elements", [])
            if item_categories:
                for cat in item_categories:
                    items_by_category[cat["id"]].append(item)
            else:
                uncategorized_items.append(item)

        # Build categories with items
        pos_categories: list[POSMenuCategory] = []
        for cat in categories_raw:
            cat_id = cat.get("id", "")
            pos_categories.append(
                POSMenuCategory(
                    external_id=cat_id,
                    name=cat.get("name", ""),
                    description="",  # Clover categories don't have descriptions
                    items=[self._parse_item(i) for i in items_by_category[cat_id]],
                )
            )

        # Add uncategorized items if any
        if uncategorized_items:
            pos_categories.append(
                POSMenuCategory(
                    external_id="uncategorized",
                    name="Other Items",
                    items=[self._parse_item(i) for i in uncategorized_items],
                )
            )

        # Return as single menu
        return [
            POSMenu(
                external_id="main",
                name="Menu",
                description="",
                categories=pos_categories,
            )
        ]

    async def get_menu(
        self, session: POSSession, location_id: str, menu_id: str
    ) -> POSMenu:
        """
        Get a specific menu by ID.

        Since Clover only has one conceptual "menu", this returns the same
        result as get_menus() for the main menu, or raises an error for
        other IDs.

        Args:
            session: Authenticated session.
            location_id: Clover merchant ID.
            menu_id: Menu identifier (only "main" is supported).

        Returns:
            The requested menu.

        Raises:
            POSAPIError: If menu_id is not "main".
        """
        if menu_id != "main":
            raise POSAPIError(
                f"Menu not found: {menu_id}. Clover only supports 'main' menu.",
                provider="clover",
                status_code=404,
            )

        menus = await self.get_menus(session, location_id)
        return menus[0]

    async def get_item_availability(
        self, session: POSSession, location_id: str
    ) -> dict[str, bool]:
        """
        Get current availability status for all items.

        Uses Clover's item_stocks endpoint for inventory tracking.

        Args:
            session: Authenticated session.
            location_id: Clover merchant ID.

        Returns:
            Dict mapping item ID to availability (True = available).

        Raises:
            POSAPIError: If the API request fails.
        """
        response = await self._request_with_retry(
            "GET",
            f"{self._base_url}/v3/merchants/{location_id}/item_stocks",
            session,
        )

        data = response.json()
        stocks = data.get("elements", [])

        availability: dict[str, bool] = {}
        for stock in stocks:
            item_ref = stock.get("item", {})
            item_id = item_ref.get("id", "")
            quantity = stock.get("quantity", 0)
            # Item is available if quantity > 0 or if stock tracking isn't enabled
            # (stockCount being null means no tracking)
            stock_count = stock.get("stockCount")
            if stock_count is None:
                availability[item_id] = True  # No tracking = always available
            else:
                availability[item_id] = quantity > 0

        return availability

    async def _fetch_categories(
        self, session: POSSession, merchant_id: str
    ) -> list[dict[str, Any]]:
        """Fetch all categories for a merchant."""
        response = await self._request_with_retry(
            "GET",
            f"{self._base_url}/v3/merchants/{merchant_id}/categories",
            session,
            params={"orderBy": "sortOrder"},
        )
        data: dict[str, Any] = response.json()
        elements: list[dict[str, Any]] = data.get("elements", [])
        return elements

    async def _fetch_items(
        self, session: POSSession, merchant_id: str
    ) -> list[dict[str, Any]]:
        """Fetch all items for a merchant with category and modifier info."""
        response = await self._request_with_retry(
            "GET",
            f"{self._base_url}/v3/merchants/{merchant_id}/items",
            session,
            params={"expand": "categories,modifierGroups"},
        )
        data: dict[str, Any] = response.json()
        elements: list[dict[str, Any]] = data.get("elements", [])
        return elements

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def _parse_item(self, raw: dict[str, Any]) -> POSMenuItem:
        """Convert Clover item format to internal POSMenuItem."""
        # Clover prices are in cents
        price_cents = raw.get("price", 0)
        price = Decimal(price_cents) / 100

        # Extract modifier groups
        modifier_groups = []
        for mg in raw.get("modifierGroups", {}).get("elements", []):
            modifier_groups.append(self._parse_modifier_group(mg))

        return POSMenuItem(
            external_id=raw.get("id", ""),
            name=raw.get("name", ""),
            description=raw.get("alternateName", ""),  # Clover uses alternateName
            price=price,
            image_url="",  # Clover images require separate API call
            is_available=not raw.get("hidden", False),
            modifier_groups=modifier_groups,
            # Clover doesn't have built-in dietary flags
            is_vegetarian=False,
            is_vegan=False,
            is_gluten_free=False,
            allergens=[],
        )

    def _parse_modifier_group(self, raw: dict[str, Any]) -> POSModifierGroup:
        """Convert Clover modifier group to internal format."""
        modifiers = []
        for mod in raw.get("modifiers", {}).get("elements", []):
            modifiers.append(self._parse_modifier(mod))

        return POSModifierGroup(
            external_id=raw.get("id", ""),
            name=raw.get("name", ""),
            min_selections=raw.get("minRequired", 0),
            max_selections=raw.get("maxAllowed", 1),
            modifiers=modifiers,
        )

    def _parse_modifier(self, raw: dict[str, Any]) -> POSModifier:
        """Convert Clover modifier to internal format."""
        price_cents = raw.get("price", 0)
        return POSModifier(
            external_id=raw.get("id", ""),
            name=raw.get("name", ""),
            price_adjustment=Decimal(price_cents) / 100,
            is_available=not raw.get("hidden", False),
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
        Create a new order in Clover.

        Note: Will be implemented in Phase 4.

        Raises:
            POSAPIError: Always - not implemented yet.
        """
        raise POSAPIError(
            "Order creation will be implemented in Phase 4",
            provider="clover",
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
            provider="clover",
        )

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """
        Verify Clover webhook signature.

        Clover uses HMAC-SHA256 for webhook authentication.

        Args:
            payload: Raw webhook payload bytes.
            signature: Value from X-Clover-Signature header.
            secret: Webhook secret configured in Clover.

        Returns:
            True if signature is valid.
        """
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature.lower(), expected.lower())

    def parse_webhook(self, payload: dict[str, Any]) -> POSWebhookEvent:
        """
        Parse a Clover webhook payload into a typed event.

        Clover webhook event types:
        - I (Inventory) updates with type=UPDATE
        - M (Menu/Item) updates with type=UPDATE

        Args:
            payload: Parsed JSON webhook payload.

        Returns:
            Typed webhook event.

        Raises:
            POSWebhookError: If payload cannot be parsed.
        """
        # Clover uses different payload structures
        # Check for different event patterns
        app_id = payload.get("appId", "")
        merchants = payload.get("merchants", {})

        if not merchants:
            raise POSWebhookError(
                "Invalid Clover webhook: missing merchants data",
                provider="clover",
            )

        # Process first merchant (typically only one per webhook)
        merchant_id = next(iter(merchants.keys()), "")
        merchant_data = merchants.get(merchant_id, {})

        # Parse timestamp
        timestamp_ms = payload.get("ts", 0)
        try:
            if timestamp_ms:
                occurred_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            else:
                occurred_at = datetime.now(UTC)
        except (ValueError, OSError) as e:
            raise POSWebhookError(
                f"Invalid timestamp in Clover webhook: {e}",
                provider="clover",
            ) from e

        event_id = f"{app_id}-{timestamp_ms}"

        # Check for inventory updates (I = Inventory)
        if "I" in merchant_data:
            inventory_updates = merchant_data.get("I", [])
            if inventory_updates:
                # Get the first inventory update
                inv_update = inventory_updates[0]
                item_id = inv_update.get("objectId", "")
                update_type = inv_update.get("type", "")

                # Inventory updates indicate stock changes
                # We'd need to fetch current stock to know availability
                # For now, treat UPDATE as availability change
                return ItemAvailabilityChangedEvent(
                    provider=POSProvider.CLOVER,
                    event_id=event_id,
                    occurred_at=occurred_at,
                    item_id=item_id,
                    is_available=update_type != "DELETE",
                )

        # Check for item/menu updates (ITEM = Item updates)
        if "ITEM" in merchant_data:
            item_updates = merchant_data.get("ITEM", [])
            if item_updates:
                item_update = item_updates[0]
                item_id = item_update.get("objectId", "")
                update_type = item_update.get("type", "")

                if update_type == "DELETE":
                    # Item was deleted
                    return ItemAvailabilityChangedEvent(
                        provider=POSProvider.CLOVER,
                        event_id=event_id,
                        occurred_at=occurred_at,
                        item_id=item_id,
                        is_available=False,
                    )

                # Item was created or updated - treat as menu update
                return MenuUpdatedEvent(
                    provider=POSProvider.CLOVER,
                    event_id=event_id,
                    occurred_at=occurred_at,
                    menu_id="main",  # Clover has single conceptual menu
                )

        # Check for category updates (CATEGORY)
        if "CATEGORY" in merchant_data:
            return MenuUpdatedEvent(
                provider=POSProvider.CLOVER,
                event_id=event_id,
                occurred_at=occurred_at,
                menu_id="main",
            )

        raise POSWebhookError(
            f"Unknown Clover webhook event type: {list(merchant_data.keys())}",
            provider="clover",
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
