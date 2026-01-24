"""Toast POS adapter - integration with Toast's restaurant platform."""

import asyncio
import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderStatus,
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


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_second: float = 1.0) -> None:
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


class ToastAdapter:
    """
    Toast POS adapter implementing the POSAdapter protocol.

    Integrates with Toast's restaurant platform for:
    - Menu synchronization
    - Item availability (86'd items)
    - Webhook event handling

    Note: Order creation requires Toast Partner API access (Phase 4).

    API Reference: https://doc.toasttab.com/
    """

    BASE_URL = "https://ws-api.toasttab.com"
    AUTH_URL = f"{BASE_URL}/authentication/v1/authentication/login"
    MENUS_URL = f"{BASE_URL}/menus/v2/menus"
    STOCK_URL = f"{BASE_URL}/stock/v1/inventory"

    # Toast rate limit: 1 request per second per restaurant
    REQUESTS_PER_SECOND = 1.0

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        """
        Initialize the Toast adapter.

        Args:
            http_client: Optional HTTP client for dependency injection (testing).
        """
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._owns_client = http_client is None

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    def _get_rate_limiter(self, location_id: str) -> RateLimiter:
        """Get or create a rate limiter for a specific location."""
        if location_id not in self._rate_limiters:
            self._rate_limiters[location_id] = RateLimiter(self.REQUESTS_PER_SECOND)
        return self._rate_limiters[location_id]

    @property
    def provider(self) -> POSProvider:
        """The POS provider this adapter connects to."""
        return POSProvider.TOAST

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        """
        Authenticate with Toast using client credentials.

        Toast uses a machine client flow - no refresh tokens, just re-authenticate
        when the access token expires.

        Args:
            credentials: Toast API credentials (client_id, client_secret).

        Returns:
            Authenticated session with access token.

        Raises:
            POSAuthError: If authentication fails.
        """
        try:
            response = await self._client.post(
                self.AUTH_URL,
                json={
                    "clientId": credentials.client_id,
                    "clientSecret": credentials.client_secret,
                    "userAccessType": "TOAST_MACHINE_CLIENT",
                },
            )

            if response.status_code == 401:
                raise POSAuthError(
                    "Invalid Toast credentials",
                    provider="toast",
                )

            response.raise_for_status()
            data = response.json()

            token_data = data.get("token", {})
            access_token = token_data.get("accessToken")
            expires_in = token_data.get("expiresIn", 86400)  # Default 24h

            if not access_token:
                raise POSAuthError(
                    "No access token in Toast response",
                    provider="toast",
                )

            return POSSession(
                provider=POSProvider.TOAST,
                access_token=access_token,
                refresh_token=None,  # Toast doesn't use refresh tokens
                expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            )

        except httpx.HTTPStatusError as e:
            raise POSAuthError(
                f"Toast authentication failed: {e.response.status_code}",
                provider="toast",
            ) from e
        except httpx.RequestError as e:
            raise POSAuthError(
                f"Toast authentication request failed: {e}",
                provider="toast",
            ) from e

    async def refresh_token(self, session: POSSession) -> POSSession:  # noqa: ARG002
        """
        Refresh an expired access token.

        Toast doesn't use refresh tokens - this method exists for protocol
        compatibility. In practice, callers should re-authenticate when the
        token expires.

        Args:
            session: Current session (credentials needed for re-auth).

        Raises:
            POSAuthError: Always - Toast doesn't support token refresh.
        """
        raise POSAuthError(
            "Toast does not support token refresh. Re-authenticate instead.",
            provider="toast",
        )

    # =========================================================================
    # HTTP Helpers
    # =========================================================================

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        session: POSSession,
        location_id: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            session: Authenticated session
            location_id: Toast restaurant GUID for rate limiting
            **kwargs: Additional arguments passed to httpx

        Returns:
            HTTP response

        Raises:
            POSAPIError: If request fails after retries
            POSRateLimitError: If rate limit exceeded
        """
        rate_limiter = self._get_rate_limiter(location_id)
        headers = {
            "Authorization": f"Bearer {session.access_token}",
            "Toast-Restaurant-External-ID": location_id,
            **kwargs.pop("headers", {}),
        }

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            await rate_limiter.acquire()

            try:
                response = await self._client.request(
                    method, url, headers=headers, **kwargs
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise POSRateLimitError(
                        "Toast rate limit exceeded",
                        provider="toast",
                        retry_after=retry_after,
                    )

                if response.status_code == 401:
                    raise POSAuthError(
                        "Toast session expired",
                        provider="toast",
                    )

                response.raise_for_status()
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.RETRY_BACKOFF_BASE**attempt
                    logger.warning(
                        "Toast API failed (attempt %d/%d), retry in %.1fs: %s",
                        attempt + 1,
                        self.MAX_RETRIES,
                        backoff,
                        str(e),
                    )
                    await asyncio.sleep(backoff)

        # All retries exhausted
        raise POSAPIError(
            f"Toast API request failed after {self.MAX_RETRIES} attempts: {last_error}",
            provider="toast",
        )

    # =========================================================================
    # Menu Operations
    # =========================================================================

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        """
        Get all menus for a Toast restaurant.

        Args:
            session: Authenticated session.
            location_id: Toast restaurant GUID.

        Returns:
            List of menus with categories and items.

        Raises:
            POSAPIError: If the API request fails.
        """
        response = await self._request_with_retry(
            "GET",
            self.MENUS_URL,
            session,
            location_id,
        )

        data = response.json()
        return [self._parse_menu(menu) for menu in data]

    async def get_menu(
        self, session: POSSession, location_id: str, menu_id: str
    ) -> POSMenu:
        """
        Get a specific menu by ID.

        Args:
            session: Authenticated session.
            location_id: Toast restaurant GUID.
            menu_id: Menu GUID in Toast.

        Returns:
            The requested menu with categories and items.

        Raises:
            POSAPIError: If the API request fails or menu not found.
        """
        response = await self._request_with_retry(
            "GET",
            f"{self.MENUS_URL}/{menu_id}",
            session,
            location_id,
        )

        data = response.json()
        return self._parse_menu(data)

    async def get_item_availability(
        self, session: POSSession, location_id: str
    ) -> dict[str, bool]:
        """
        Get current availability status for all items.

        Uses Toast's stock/inventory API to check 86'd status.

        Args:
            session: Authenticated session.
            location_id: Toast restaurant GUID.

        Returns:
            Dict mapping item GUID to availability (True = available).

        Raises:
            POSAPIError: If the API request fails.
        """
        response = await self._request_with_retry(
            "GET",
            self.STOCK_URL,
            session,
            location_id,
        )

        data = response.json()
        availability: dict[str, bool] = {}

        # Toast returns stock items with outOfStock boolean
        for item in data.get("stockItems", []):
            item_guid = item.get("guid", "")
            is_out_of_stock = item.get("outOfStock", False)
            availability[item_guid] = not is_out_of_stock

        return availability

    # =========================================================================
    # Order Operations
    # =========================================================================

    ORDERS_URL = f"{BASE_URL}/orders/v2/orders"

    async def create_order(
        self,
        session: POSSession,  # noqa: ARG002
        location_id: str,  # noqa: ARG002
        order: POSOrder,
    ) -> POSOrderResult:
        """
        Create a new order in Toast.

        Note: Full implementation requires Toast Partner API access.
        Currently uses placeholder mode that simulates success for demos.
        When Partner API is configured, this will POST to /orders/v2/orders.

        Args:
            session: Authenticated session (unused in placeholder mode).
            location_id: Toast restaurant GUID (unused in placeholder mode).
            order: Order details to submit.

        Returns:
            Result with POS order ID and estimated ready time.
        """
        logger.info(
            "Toast order submission (placeholder mode): %s items for %s",
            len(order.items),
            order.customer_name,
        )

        order_id = f"toast-{uuid.uuid4().hex[:12]}"
        confirmation_code = uuid.uuid4().hex[:6].upper()
        estimated_ready = datetime.now(UTC) + timedelta(minutes=25)

        return POSOrderResult(
            external_id=order_id,
            status=OrderStatus.CONFIRMED,
            estimated_ready_time=estimated_ready,
            confirmation_code=confirmation_code,
        )

    async def get_order_status(
        self,
        session: POSSession,  # noqa: ARG002
        location_id: str,  # noqa: ARG002
        order_id: str,
    ) -> POSOrderStatus:
        """
        Get current status of an order.

        Note: Full implementation requires Toast Partner API access.
        Currently returns a placeholder status for demos.
        When Partner API is configured, this will GET /orders/v2/orders/{id}.

        Args:
            session: Authenticated session (unused in placeholder mode).
            location_id: Toast restaurant GUID (unused in placeholder mode).
            order_id: Order ID in Toast.

        Returns:
            Current order status.
        """
        logger.info("Toast order status check (placeholder mode): %s", order_id)

        return POSOrderStatus(
            external_id=order_id,
            status=OrderStatus.CONFIRMED,
            estimated_ready_time=datetime.now(UTC) + timedelta(minutes=20),
            updated_at=datetime.now(UTC),
        )

    # =========================================================================
    # Parsing Helpers
    # =========================================================================

    def _parse_menu(self, raw: dict[str, Any]) -> POSMenu:
        """Convert Toast menu format to internal POSMenu."""
        return POSMenu(
            external_id=raw.get("guid", ""),
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            available_start=self._parse_time_of_day(raw.get("availability", {})),
            available_end=self._parse_time_of_day(
                raw.get("availability", {}), start=False
            ),
            categories=[
                self._parse_category(group) for group in raw.get("menuGroups", [])
            ],
        )

    def _parse_time_of_day(
        self, availability: dict[str, Any], start: bool = True
    ) -> str | None:
        """Extract start or end time from Toast availability object."""
        key = "startTime" if start else "endTime"
        time_val: str | None = availability.get(key)
        if time_val:
            # Toast returns time as "HH:MM:SS", we want "HH:MM"
            return time_val[:5] if len(time_val) >= 5 else time_val
        return None

    def _parse_category(self, raw: dict[str, Any]) -> POSMenuCategory:
        """Convert Toast menu group to internal POSMenuCategory."""
        return POSMenuCategory(
            external_id=raw.get("guid", ""),
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            items=[self._parse_item(item) for item in raw.get("menuItems", [])],
        )

    def _parse_item(self, raw: dict[str, Any]) -> POSMenuItem:
        """Convert Toast menu item to internal POSMenuItem."""
        # Extract price - Toast uses cents or has nested price object
        price = self._extract_price(raw)

        # Extract dietary info from Toast's item tags
        tags = {tag.get("name", "").lower() for tag in raw.get("tags", [])}

        return POSMenuItem(
            external_id=raw.get("guid", ""),
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            price=price,
            image_url=raw.get("imageUrl", "") or raw.get("image", ""),
            is_available=raw.get("visibility", "ALL") != "NONE",
            is_vegetarian="vegetarian" in tags,
            is_vegan="vegan" in tags,
            is_gluten_free="gluten-free" in tags or "gluten free" in tags,
            allergens=self._extract_allergens(raw),
            modifier_groups=[
                self._parse_modifier_group(mg) for mg in raw.get("modifierGroups", [])
            ],
        )

    def _extract_price(self, raw: dict[str, Any]) -> Decimal:
        """Extract price from Toast item, handling various formats."""
        # Direct price field (in dollars)
        if "price" in raw:
            return Decimal(str(raw["price"]))
        # Nested price object
        if raw.get("prices"):
            first_price = raw["prices"][0]
            return Decimal(str(first_price.get("price", 0)))
        return Decimal("0.00")

    def _extract_allergens(self, raw: dict[str, Any]) -> list[str]:
        """Extract allergen list from Toast item."""
        allergens: list[str] = []
        # Toast may have allergens in tags or dedicated field
        for tag in raw.get("tags", []):
            tag_name = tag.get("name", "").lower()
            if "allergen:" in tag_name:
                allergens.append(tag_name.replace("allergen:", "").strip())
        # Also check dedicated allergens field if present
        if "allergens" in raw:
            allergens.extend(raw["allergens"])
        return allergens

    def _parse_modifier_group(self, raw: dict[str, Any]) -> POSModifierGroup:
        """Convert Toast modifier group to internal format."""
        return POSModifierGroup(
            external_id=raw.get("guid", ""),
            name=raw.get("name", ""),
            min_selections=raw.get("minSelections", 0),
            max_selections=raw.get("maxSelections", 1),
            modifiers=[self._parse_modifier(mod) for mod in raw.get("modifiers", [])],
        )

    def _parse_modifier(self, raw: dict[str, Any]) -> POSModifier:
        """Convert Toast modifier to internal format."""
        return POSModifier(
            external_id=raw.get("guid", ""),
            name=raw.get("name", ""),
            price_adjustment=Decimal(str(raw.get("price", 0))),
            is_available=raw.get("visibility", "ALL") != "NONE",
        )

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """
        Verify Toast webhook signature.

        Toast uses HMAC-SHA256 for webhook authentication.
        Signature is sent in the Toast-Signature header.

        Args:
            payload: Raw webhook payload bytes.
            signature: Value from Toast-Signature header.
            secret: Webhook secret configured in Toast.

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
        Parse a Toast webhook payload into a typed event.

        Toast webhook event types:
        - MENU_UPDATED: Menu configuration changed
        - ITEM_AVAILABILITY_CHANGED: Item 86'd status changed (stock)

        Args:
            payload: Parsed JSON webhook payload.

        Returns:
            Typed webhook event.

        Raises:
            POSWebhookError: If payload cannot be parsed.
        """
        event_type = payload.get("eventType", "")
        event_id = payload.get("eventId", payload.get("webhookId", ""))

        # Parse timestamp - Toast uses ISO format
        occurred_at_str = payload.get("occurredAt", payload.get("timestamp"))
        try:
            if occurred_at_str:
                occurred_at = datetime.fromisoformat(
                    occurred_at_str.replace("Z", "+00:00")
                )
            else:
                occurred_at = datetime.now(UTC)
        except ValueError as e:
            raise POSWebhookError(
                f"Invalid timestamp in Toast webhook: {e}",
                provider="toast",
            ) from e

        if event_type == "MENU_UPDATED":
            menu_id = payload.get("menuGuid", payload.get("entityGuid", ""))
            return MenuUpdatedEvent(
                provider=POSProvider.TOAST,
                event_id=event_id,
                occurred_at=occurred_at,
                menu_id=menu_id,
            )

        elif event_type == "ITEM_AVAILABILITY_CHANGED":
            # Toast sends stock updates with item details
            item_id = payload.get("itemGuid", payload.get("entityGuid", ""))
            is_available = not payload.get("outOfStock", False)
            return ItemAvailabilityChangedEvent(
                provider=POSProvider.TOAST,
                event_id=event_id,
                occurred_at=occurred_at,
                item_id=item_id,
                is_available=is_available,
            )

        else:
            raise POSWebhookError(
                f"Unknown Toast webhook event type: {event_type}",
                provider="toast",
            )
