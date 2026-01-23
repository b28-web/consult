"""Mock POS adapter for development and testing."""

import asyncio
import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderStatus,
    OrderStatusChangedEvent,
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
    POSOrderError,
    POSWebhookError,
)


def _default_menus() -> list[POSMenu]:
    """Generate default test menus."""
    return [
        POSMenu(
            external_id="menu-breakfast",
            name="Breakfast",
            description="Morning favorites",
            available_start="06:00",
            available_end="11:00",
            categories=[
                POSMenuCategory(
                    external_id="cat-eggs",
                    name="Eggs & Omelets",
                    items=[
                        POSMenuItem(
                            external_id="item-scrambled",
                            name="Scrambled Eggs",
                            description="Three farm-fresh eggs scrambled with butter",
                            price=Decimal("8.99"),
                            is_vegetarian=True,
                            modifier_groups=[
                                POSModifierGroup(
                                    external_id="mod-cheese",
                                    name="Add Cheese",
                                    min_selections=0,
                                    max_selections=1,
                                    modifiers=[
                                        POSModifier(
                                            external_id="mod-cheddar",
                                            name="Cheddar",
                                            price_adjustment=Decimal("1.50"),
                                        ),
                                        POSModifier(
                                            external_id="mod-swiss",
                                            name="Swiss",
                                            price_adjustment=Decimal("1.50"),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        POSMenuItem(
                            external_id="item-omelet",
                            name="Western Omelet",
                            description="Ham, peppers, onions, and cheese",
                            price=Decimal("12.99"),
                            allergens=["dairy"],
                        ),
                    ],
                ),
                POSMenuCategory(
                    external_id="cat-pancakes",
                    name="Pancakes & Waffles",
                    items=[
                        POSMenuItem(
                            external_id="item-pancakes",
                            name="Buttermilk Pancakes",
                            description="Stack of three fluffy pancakes",
                            price=Decimal("9.99"),
                            is_vegetarian=True,
                            allergens=["gluten", "dairy"],
                        ),
                    ],
                ),
            ],
        ),
        POSMenu(
            external_id="menu-lunch",
            name="Lunch",
            description="Midday meals",
            available_start="11:00",
            available_end="16:00",
            categories=[
                POSMenuCategory(
                    external_id="cat-sandwiches",
                    name="Sandwiches",
                    items=[
                        POSMenuItem(
                            external_id="item-club",
                            name="Club Sandwich",
                            description="Turkey, bacon, lettuce, tomato on toast",
                            price=Decimal("13.99"),
                            allergens=["gluten"],
                        ),
                        POSMenuItem(
                            external_id="item-veggie-wrap",
                            name="Veggie Wrap",
                            description="Fresh vegetables with hummus",
                            price=Decimal("11.99"),
                            is_vegetarian=True,
                            is_vegan=True,
                            allergens=["gluten"],
                        ),
                    ],
                ),
            ],
        ),
    ]


class MockPOSAdapter:
    """
    Mock POS adapter for development and testing.

    Provides configurable behavior for simulating:
    - Menu data
    - Item availability (86'd items)
    - Order creation success/failure
    - Authentication delays

    Usage:
        adapter = MockPOSAdapter(
            menus=custom_menus,
            unavailable_items={"item-scrambled"},
            fail_orders=True,
        )
    """

    def __init__(
        self,
        menus: list[POSMenu] | None = None,
        unavailable_items: set[str] | None = None,
        fail_orders: bool = False,
        fail_auth: bool = False,
        auth_delay_ms: int = 0,
        api_delay_ms: int = 0,
    ) -> None:
        """
        Initialize mock adapter.

        Args:
            menus: Custom menus to return. Uses default test menus if None.
            unavailable_items: Set of item external_ids to mark as 86'd.
            fail_orders: If True, order creation will fail.
            fail_auth: If True, authentication will fail.
            auth_delay_ms: Simulated auth delay in milliseconds.
            api_delay_ms: Simulated API delay in milliseconds.
        """
        self._menus = menus if menus is not None else _default_menus()
        self._unavailable_items = unavailable_items or set()
        self._fail_orders = fail_orders
        self._fail_auth = fail_auth
        self._auth_delay_ms = auth_delay_ms
        self._api_delay_ms = api_delay_ms

        # Track created orders for status queries
        self._orders: dict[str, POSOrderStatus] = {}

    @property
    def provider(self) -> POSProvider:
        """The POS provider this adapter connects to."""
        return POSProvider.MOCK

    # =========================================================================
    # Configuration methods (for test setup)
    # =========================================================================

    def set_item_unavailable(self, item_id: str) -> None:
        """Mark an item as 86'd (unavailable)."""
        self._unavailable_items.add(item_id)

    def set_item_available(self, item_id: str) -> None:
        """Mark an item as available."""
        self._unavailable_items.discard(item_id)

    def set_order_status(self, order_id: str, status: OrderStatus) -> None:
        """Update the status of a tracked order."""
        if order_id in self._orders:
            self._orders[order_id] = POSOrderStatus(
                external_id=order_id,
                status=status,
                updated_at=datetime.now(UTC),
            )

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(
        self,
        credentials: POSCredentials,  # noqa: ARG002
    ) -> POSSession:
        """Authenticate with the mock POS provider."""
        if self._auth_delay_ms > 0:
            await asyncio.sleep(self._auth_delay_ms / 1000)

        if self._fail_auth:
            raise POSAuthError("Mock authentication failure", provider="mock")

        return POSSession(
            provider=POSProvider.MOCK,
            access_token=f"mock-token-{uuid.uuid4().hex[:8]}",
            refresh_token=f"mock-refresh-{uuid.uuid4().hex[:8]}",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    async def refresh_token(self, session: POSSession) -> POSSession:
        """Refresh an expired access token."""
        if self._auth_delay_ms > 0:
            await asyncio.sleep(self._auth_delay_ms / 1000)

        if self._fail_auth:
            raise POSAuthError("Mock token refresh failure", provider="mock")

        return POSSession(
            provider=POSProvider.MOCK,
            access_token=f"mock-token-{uuid.uuid4().hex[:8]}",
            refresh_token=session.refresh_token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    # =========================================================================
    # Menu Operations
    # =========================================================================

    async def get_menus(
        self,
        session: POSSession,
        location_id: str,  # noqa: ARG002
    ) -> list[POSMenu]:
        """Get all menus for a location."""
        if self._api_delay_ms > 0:
            await asyncio.sleep(self._api_delay_ms / 1000)

        # Apply availability status to items
        menus = []
        for menu in self._menus:
            categories = []
            for category in menu.categories:
                items = [
                    item.model_copy(
                        update={
                            "is_available": item.external_id
                            not in self._unavailable_items
                        }
                    )
                    for item in category.items
                ]
                categories.append(category.model_copy(update={"items": items}))
            menus.append(menu.model_copy(update={"categories": categories}))

        return menus

    async def get_menu(
        self,
        session: POSSession,
        location_id: str,
        menu_id: str,
    ) -> POSMenu:
        """Get a specific menu by ID."""
        if self._api_delay_ms > 0:
            await asyncio.sleep(self._api_delay_ms / 1000)

        for menu in self._menus:
            if menu.external_id == menu_id:
                # Apply availability status
                categories = []
                for category in menu.categories:
                    items = [
                        item.model_copy(
                            update={
                                "is_available": item.external_id
                                not in self._unavailable_items
                            }
                        )
                        for item in category.items
                    ]
                    categories.append(category.model_copy(update={"items": items}))
                return menu.model_copy(update={"categories": categories})

        raise POSAPIError(
            f"Menu not found: {menu_id}",
            provider="mock",
            status_code=404,
        )

    async def get_item_availability(
        self,
        session: POSSession,
        location_id: str,  # noqa: ARG002
    ) -> dict[str, bool]:
        """Get current availability status for all items."""
        if self._api_delay_ms > 0:
            await asyncio.sleep(self._api_delay_ms / 1000)

        availability: dict[str, bool] = {}
        for menu in self._menus:
            for category in menu.categories:
                for item in category.items:
                    availability[item.external_id] = (
                        item.external_id not in self._unavailable_items
                    )

        return availability

    # =========================================================================
    # Order Operations
    # =========================================================================

    async def create_order(
        self,
        session: POSSession,
        location_id: str,
        order: POSOrder,
    ) -> POSOrderResult:
        """Create a new order in the mock POS system."""
        if self._api_delay_ms > 0:
            await asyncio.sleep(self._api_delay_ms / 1000)

        if self._fail_orders:
            raise POSOrderError(
                "Mock order creation failure",
                provider="mock",
            )

        # Check if any items are unavailable
        for item in order.items:
            if item.menu_item_external_id in self._unavailable_items:
                raise POSOrderError(
                    f"Item is unavailable: {item.menu_item_external_id}",
                    provider="mock",
                )

        # Create order
        order_id = f"mock-order-{uuid.uuid4().hex[:8]}"
        estimated_ready = datetime.now(UTC) + timedelta(minutes=20)

        # Track order for status queries
        self._orders[order_id] = POSOrderStatus(
            external_id=order_id,
            status=OrderStatus.CONFIRMED,
            estimated_ready_time=estimated_ready,
            updated_at=datetime.now(UTC),
        )

        return POSOrderResult(
            external_id=order_id,
            status=OrderStatus.CONFIRMED,
            estimated_ready_time=estimated_ready,
            confirmation_code=uuid.uuid4().hex[:6].upper(),
        )

    async def get_order_status(
        self,
        session: POSSession,
        location_id: str,
        order_id: str,
    ) -> POSOrderStatus:
        """Get current status of an order."""
        if self._api_delay_ms > 0:
            await asyncio.sleep(self._api_delay_ms / 1000)

        if order_id in self._orders:
            return self._orders[order_id]

        raise POSAPIError(
            f"Order not found: {order_id}",
            provider="mock",
            status_code=404,
        )

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify webhook signature using HMAC-SHA256."""
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def parse_webhook(self, payload: dict[str, Any]) -> POSWebhookEvent:
        """Parse a webhook payload into a typed event."""
        event_type = payload.get("event_type")
        if not event_type:
            raise POSWebhookError("Missing event_type in payload", provider="mock")

        try:
            occurred_at = datetime.fromisoformat(
                payload.get("occurred_at", datetime.now(UTC).isoformat())
            )
        except ValueError as e:
            raise POSWebhookError(f"Invalid occurred_at: {e}", provider="mock") from e

        event_id = payload.get("event_id", uuid.uuid4().hex)

        if event_type == "menu_updated":
            return MenuUpdatedEvent(
                provider=POSProvider.MOCK,
                event_id=event_id,
                occurred_at=occurred_at,
                menu_id=payload.get("menu_id", ""),
            )
        elif event_type == "item_availability_changed":
            return ItemAvailabilityChangedEvent(
                provider=POSProvider.MOCK,
                event_id=event_id,
                occurred_at=occurred_at,
                item_id=payload.get("item_id", ""),
                is_available=payload.get("is_available", True),
            )
        elif event_type == "order_status_changed":
            return OrderStatusChangedEvent(
                provider=POSProvider.MOCK,
                event_id=event_id,
                occurred_at=occurred_at,
                order_id=payload.get("order_id", ""),
                status=OrderStatus(payload.get("status", "pending")),
                previous_status=(
                    OrderStatus(payload["previous_status"])
                    if payload.get("previous_status")
                    else None
                ),
            )
        else:
            raise POSWebhookError(f"Unknown event type: {event_type}", provider="mock")
