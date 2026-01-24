"""Tests for SquareAdapter - comprehensive mocked API tests."""

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
import respx
from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderType,
    POSCredentials,
    POSOrder,
    POSOrderItem,
    POSProvider,
    POSSession,
)

from apps.web.pos.adapters import SquareAdapter, get_adapter
from apps.web.pos.adapters.base import POSAdapter
from apps.web.pos.exceptions import (
    POSAPIError,
    POSAuthError,
    POSRateLimitError,
    POSWebhookError,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> SquareAdapter:
    """Create a Square adapter for testing."""
    return SquareAdapter(sandbox=True)


@pytest.fixture
def credentials() -> POSCredentials:
    """Create test Square credentials."""
    return POSCredentials(
        provider=POSProvider.SQUARE,
        client_id="square-app-id",
        client_secret="square-app-secret",
        location_id="location-12345",
        extra={"auth_code": "auth-code-xyz"},
    )


@pytest.fixture
def session() -> POSSession:
    """Create a test Square session."""
    return POSSession(
        provider=POSProvider.SQUARE,
        access_token="square-access-token-abc",
        refresh_token="square-refresh-token-xyz",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )


@pytest.fixture
def square_catalog_response() -> dict:
    """Sample Square catalog search API response."""
    return {
        "objects": [
            {
                "type": "CATEGORY",
                "id": "cat-001",
                "category_data": {"name": "Appetizers"},
            },
            {
                "type": "CATEGORY",
                "id": "cat-002",
                "category_data": {"name": "Entrees"},
            },
            {
                "type": "ITEM",
                "id": "item-001",
                "item_data": {
                    "name": "Crispy Calamari",
                    "description": "Lightly fried with marinara",
                    "category_id": "cat-001",
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": "var-001",
                            "item_variation_data": {
                                "name": "Regular",
                                "price_money": {"amount": 1499, "currency": "USD"},
                            },
                        }
                    ],
                    "modifier_list_info": [
                        {
                            "modifier_list_id": "mod-list-001",
                            "min_selected_modifiers": 0,
                            "max_selected_modifiers": 2,
                        }
                    ],
                },
            },
            {
                "type": "ITEM",
                "id": "item-002",
                "item_data": {
                    "name": "Garden Salad",
                    "description": "Fresh mixed greens",
                    "category_id": "cat-001",
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": "var-002",
                            "item_variation_data": {
                                "name": "Regular",
                                "price_money": {"amount": 999, "currency": "USD"},
                            },
                        }
                    ],
                    "modifier_list_info": [],
                },
            },
            {
                "type": "ITEM",
                "id": "item-003",
                "item_data": {
                    "name": "Grilled Salmon",
                    "description": "Atlantic salmon with lemon butter",
                    "category_id": "cat-002",
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": "var-003",
                            "item_variation_data": {
                                "name": "Regular",
                                "price_money": {"amount": 2899, "currency": "USD"},
                            },
                        }
                    ],
                    "modifier_list_info": [],
                },
            },
            {
                "type": "ITEM",
                "id": "item-004",
                "item_data": {
                    "name": "Special Item",
                    "description": "No category item",
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": "var-004",
                            "item_variation_data": {
                                "name": "Regular",
                                "price_money": {"amount": 1299, "currency": "USD"},
                            },
                        }
                    ],
                    "modifier_list_info": [],
                },
            },
        ],
        "related_objects": [
            {
                "type": "MODIFIER_LIST",
                "id": "mod-list-001",
                "modifier_list_data": {
                    "name": "Sauce Choice",
                    "modifiers": [
                        {
                            "type": "MODIFIER",
                            "id": "mod-001",
                            "modifier_data": {
                                "name": "Extra Marinara",
                                "price_money": {"amount": 150, "currency": "USD"},
                            },
                        },
                        {
                            "type": "MODIFIER",
                            "id": "mod-002",
                            "modifier_data": {
                                "name": "Aioli",
                                "price_money": {"amount": 200, "currency": "USD"},
                            },
                        },
                    ],
                },
            }
        ],
    }


@pytest.fixture
def square_inventory_response() -> dict:
    """Sample Square inventory batch-retrieve API response."""
    return {
        "counts": [
            {
                "catalog_object_id": "var-001",
                "state": "IN_STOCK",
                "quantity": "10",
            },
            {
                "catalog_object_id": "var-002",
                "state": "IN_STOCK",
                "quantity": "5",
            },
            {
                "catalog_object_id": "var-003",
                "state": "NONE",
                "quantity": "0",
            },
            {
                "catalog_object_id": "var-004",
                "state": "IN_STOCK",
                "quantity": "3",
            },
        ]
    }


# =============================================================================
# Authentication Tests
# =============================================================================


class TestSquareAuthentication:
    """Tests for Square OAuth authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_success(self, adapter, credentials):
        """Test successful Square authentication."""
        respx.post(f"{adapter._base_url}/oauth2/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "square-token-abc123",
                    "refresh_token": "square-refresh-xyz",
                    "expires_at": "2026-02-23T12:00:00Z",
                    "merchant_id": "merchant-12345",
                },
            )
        )

        session = await adapter.authenticate(credentials)

        assert session.provider == POSProvider.SQUARE
        assert session.access_token == "square-token-abc123"
        assert session.refresh_token == "square-refresh-xyz"
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_authenticate_missing_auth_code(self, adapter):
        """Test authentication fails without auth_code."""
        credentials = POSCredentials(
            provider=POSProvider.SQUARE,
            client_id="square-app-id",
            client_secret="square-app-secret",
            location_id="location-12345",
            extra={},
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "auth_code" in str(exc_info.value)
        assert exc_info.value.provider == "square"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_invalid_credentials(self, adapter, credentials):
        """Test authentication with invalid credentials."""
        respx.post(f"{adapter._base_url}/oauth2/token").mock(
            return_value=httpx.Response(
                401,
                json={"error": "Invalid credentials"},
            )
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "Invalid Square credentials" in str(exc_info.value)
        assert exc_info.value.provider == "square"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_server_error(self, adapter, credentials):
        """Test authentication when Square API returns server error."""
        respx.post(f"{adapter._base_url}/oauth2/token").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        with pytest.raises(POSAuthError):
            await adapter.authenticate(credentials)

    @pytest.mark.asyncio
    @respx.mock
    async def test_refresh_token_success(self, adapter, session, credentials):
        """Test successful token refresh."""
        respx.post(f"{adapter._base_url}/oauth2/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "expires_at": "2026-03-23T12:00:00Z",
                },
            )
        )

        new_session = await adapter.refresh_token(session, credentials)

        assert new_session.access_token == "new-access-token"
        assert new_session.refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_token_no_refresh_token(self, adapter, credentials):
        """Test refresh fails without refresh token."""
        session = POSSession(
            provider=POSProvider.SQUARE,
            access_token="access-token",
            refresh_token=None,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.refresh_token(session, credentials)

        assert "No refresh token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_no_credentials(self, adapter, session):
        """Test refresh fails without credentials."""
        with pytest.raises(POSAuthError) as exc_info:
            await adapter.refresh_token(session, None)

        assert "requires credentials" in str(exc_info.value)


# =============================================================================
# Menu Operation Tests
# =============================================================================


class TestSquareMenuOperations:
    """Tests for menu fetching from Square API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menus_success(self, adapter, session, square_catalog_response):
        """Test fetching all menus from Square."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")

        assert len(menus) == 1
        menu = menus[0]
        assert menu.external_id == "main"
        assert menu.name == "Menu"
        # 2 categories + 1 uncategorized
        assert len(menu.categories) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_categories_parsed_correctly(
        self, adapter, session, square_catalog_response
    ):
        """Test that menu categories are correctly parsed."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")

        # Find appetizers category
        appetizers = next(
            (c for c in menus[0].categories if c.name == "Appetizers"), None
        )
        assert appetizers is not None
        assert appetizers.external_id == "cat-001"
        assert len(appetizers.items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_items_parsed_correctly(
        self, adapter, session, square_catalog_response
    ):
        """Test that menu items are correctly parsed with all fields."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")
        appetizers = next(
            (c for c in menus[0].categories if c.name == "Appetizers"), None
        )
        calamari = next(
            (i for i in appetizers.items if i.name == "Crispy Calamari"), None
        )

        assert calamari.external_id == "item-001"
        assert calamari.name == "Crispy Calamari"
        assert calamari.description == "Lightly fried with marinara"
        assert calamari.price == Decimal("14.99")

    @pytest.mark.asyncio
    @respx.mock
    async def test_uncategorized_items_grouped(
        self, adapter, session, square_catalog_response
    ):
        """Test that items without categories are grouped in 'Other Items'."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")
        other_category = next(
            (c for c in menus[0].categories if c.name == "Other Items"), None
        )

        assert other_category is not None
        assert other_category.external_id == "uncategorized"
        assert len(other_category.items) == 1
        assert other_category.items[0].name == "Special Item"

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifier_groups_parsed(
        self, adapter, session, square_catalog_response
    ):
        """Test that modifier groups are correctly parsed."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")
        appetizers = next(
            (c for c in menus[0].categories if c.name == "Appetizers"), None
        )
        calamari = next(
            (i for i in appetizers.items if i.name == "Crispy Calamari"), None
        )

        assert len(calamari.modifier_groups) == 1
        sauce_group = calamari.modifier_groups[0]
        assert sauce_group.name == "Sauce Choice"
        assert sauce_group.min_selections == 0
        assert sauce_group.max_selections == 2
        assert len(sauce_group.modifiers) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifiers_parsed(self, adapter, session, square_catalog_response):
        """Test that individual modifiers are correctly parsed."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menus = await adapter.get_menus(session, "location-12345")
        appetizers = next(
            (c for c in menus[0].categories if c.name == "Appetizers"), None
        )
        calamari = next(
            (i for i in appetizers.items if i.name == "Crispy Calamari"), None
        )
        aioli = next(
            (m for m in calamari.modifier_groups[0].modifiers if m.name == "Aioli"),
            None,
        )

        assert aioli.external_id == "mod-002"
        assert aioli.name == "Aioli"
        assert aioli.price_adjustment == Decimal("2.00")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menu_by_id_main(self, adapter, session, square_catalog_response):
        """Test fetching the main menu by ID."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )

        menu = await adapter.get_menu(session, "location-12345", "main")

        assert menu.external_id == "main"
        assert menu.name == "Menu"

    @pytest.mark.asyncio
    async def test_get_menu_by_id_not_found(self, adapter, session):
        """Test fetching a non-existent menu ID raises error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menu(session, "location-12345", "nonexistent")

        assert "Menu not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_catalog_pagination(self, adapter, session):
        """Test that catalog pagination works correctly."""
        # First page with cursor
        first_page = {
            "objects": [
                {
                    "type": "ITEM",
                    "id": "item-001",
                    "item_data": {
                        "name": "Item 1",
                        "variations": [
                            {
                                "id": "var-001",
                                "item_variation_data": {
                                    "name": "Regular",
                                    "price_money": {"amount": 100},
                                },
                            }
                        ],
                    },
                }
            ],
            "cursor": "next-page-cursor",
        }

        # Second page without cursor
        second_page = {
            "objects": [
                {
                    "type": "ITEM",
                    "id": "item-002",
                    "item_data": {
                        "name": "Item 2",
                        "variations": [
                            {
                                "id": "var-002",
                                "item_variation_data": {
                                    "name": "Regular",
                                    "price_money": {"amount": 200},
                                },
                            }
                        ],
                    },
                }
            ],
        }

        route = respx.post(f"{adapter._base_url}/v2/catalog/search")
        route.side_effect = [
            httpx.Response(200, json=first_page),
            httpx.Response(200, json=second_page),
        ]

        menus = await adapter.get_menus(session, "location-12345")

        assert route.call_count == 2
        # Both items should be in uncategorized
        other_items = next(
            (c for c in menus[0].categories if c.name == "Other Items"), None
        )
        assert other_items is not None
        assert len(other_items.items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_item_availability(
        self, adapter, session, square_catalog_response, square_inventory_response
    ):
        """Test fetching item availability from inventory API."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(200, json=square_catalog_response)
        )
        respx.post(f"{adapter._base_url}/v2/inventory/counts/batch-retrieve").mock(
            return_value=httpx.Response(200, json=square_inventory_response)
        )

        availability = await adapter.get_item_availability(session, "location-12345")

        # item-001 (var-001) is IN_STOCK with quantity 10
        assert availability["item-001"] is True
        # item-002 (var-002) is IN_STOCK with quantity 5
        assert availability["item-002"] is True
        # item-003 (var-003) is NONE with quantity 0 - out of stock
        assert availability["item-003"] is False
        # item-004 (var-004) is IN_STOCK with quantity 3
        assert availability["item-004"] is True


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestSquareErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_error(self, adapter, session):
        """Test that rate limit errors are handled correctly."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(POSRateLimitError) as exc_info:
            await adapter.get_menus(session, "location-12345")

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_invalid_error(self, adapter, session):
        """Test that invalid session triggers auth error."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(401, json={"error": "Invalid token"})
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.get_menus(session, "location-12345")

        assert "expired or invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_transient_error(
        self, adapter, session, square_catalog_response
    ):
        """Test that transient errors trigger retries."""
        route = respx.post(f"{adapter._base_url}/v2/catalog/search")
        route.side_effect = [
            httpx.Response(503, json={"error": "Service unavailable"}),
            httpx.Response(200, json=square_catalog_response),
        ]

        menus = await adapter.get_menus(session, "location-12345")

        assert len(menus) == 1
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exceeded(self, adapter, session):
        """Test that API error is raised after max retries."""
        respx.post(f"{adapter._base_url}/v2/catalog/search").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menus(session, "location-12345")

        assert "after 3 attempts" in str(exc_info.value)


# =============================================================================
# Webhook Tests
# =============================================================================


class TestSquareWebhooks:
    """Tests for Square webhook handling."""

    def test_verify_webhook_signature_valid(self, adapter):
        """Test valid webhook signature verification."""
        payload = b'{"type": "inventory.count.updated"}'
        url = "https://example.com/webhooks/square"
        secret = "webhook-secret-xyz"

        combined = url.encode() + payload
        signature = base64.b64encode(
            hmac.new(secret.encode(), combined, hashlib.sha256).digest()
        ).decode()

        assert adapter.verify_webhook_signature(payload, signature, secret, url) is True

    def test_verify_webhook_signature_invalid(self, adapter):
        """Test invalid webhook signature rejection."""
        payload = b'{"type": "inventory.count.updated"}'
        url = "https://example.com/webhooks/square"
        secret = "webhook-secret-xyz"

        result = adapter.verify_webhook_signature(payload, "invalid-sig", secret, url)

        assert result is False

    def test_verify_webhook_signature_no_url(self, adapter):
        """Test that signature verification without URL returns True (warn)."""
        payload = b'{"type": "inventory.count.updated"}'
        secret = "webhook-secret-xyz"

        # Without URL, should return True with warning
        result = adapter.verify_webhook_signature(payload, "any-sig", secret, None)

        assert result is True

    def test_parse_webhook_inventory_updated(self, adapter):
        """Test parsing inventory.count.updated webhook event."""
        payload = {
            "type": "inventory.count.updated",
            "event_id": "evt-12345",
            "created_at": "2026-01-23T15:30:00Z",
            "data": {
                "object": {
                    "inventory_counts": [
                        {
                            "catalog_object_id": "var-001",
                            "state": "IN_STOCK",
                            "quantity": "5",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.provider == POSProvider.SQUARE
        assert event.event_id == "evt-12345"
        assert event.item_id == "var-001"
        assert event.is_available is True

    def test_parse_webhook_inventory_out_of_stock(self, adapter):
        """Test parsing webhook for out-of-stock item."""
        payload = {
            "type": "inventory.count.updated",
            "event_id": "evt-12345",
            "created_at": "2026-01-23T15:30:00Z",
            "data": {
                "object": {
                    "inventory_counts": [
                        {
                            "catalog_object_id": "var-001",
                            "state": "NONE",
                            "quantity": "0",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.is_available is False

    def test_parse_webhook_catalog_updated(self, adapter):
        """Test parsing catalog.version.updated webhook event."""
        payload = {
            "type": "catalog.version.updated",
            "event_id": "evt-67890",
            "created_at": "2026-01-23T16:00:00Z",
            "data": {"object": {"catalog_version": 123}},
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.provider == POSProvider.SQUARE
        assert event.event_id == "evt-67890"
        assert event.menu_id == "main"

    def test_parse_webhook_unknown_event_type(self, adapter):
        """Test parsing unknown webhook event type raises error."""
        payload = {
            "type": "unknown.event.type",
            "event_id": "evt-00000",
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Unknown Square webhook event type" in str(exc_info.value)

    def test_parse_webhook_no_inventory_counts(self, adapter):
        """Test parsing inventory webhook without counts raises error."""
        payload = {
            "type": "inventory.count.updated",
            "event_id": "evt-12345",
            "created_at": "2026-01-23T15:30:00Z",
            "data": {"object": {"inventory_counts": []}},
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "No inventory counts" in str(exc_info.value)


# =============================================================================
# Order Operation Tests (Phase 4 - Not Implemented)
# =============================================================================


class TestSquareOrderOperations:
    """Tests for order operations (currently not implemented)."""

    @pytest.mark.asyncio
    async def test_create_order_not_implemented(self, adapter, session):
        """Test that order creation raises not implemented error."""
        order = POSOrder(
            customer_name="Test",
            customer_email="test@test.com",
            order_type=OrderType.PICKUP,
            items=[
                POSOrderItem(
                    menu_item_external_id="item-001",
                    name="Test Item",
                    unit_price=Decimal("10.00"),
                )
            ],
            subtotal=Decimal("10.00"),
            tax=Decimal("0.80"),
            total=Decimal("10.80"),
        )

        with pytest.raises(POSAPIError) as exc_info:
            await adapter.create_order(session, "location-12345", order)

        assert "Phase 4" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_status_not_implemented(self, adapter, session):
        """Test that order status raises not implemented error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_order_status(session, "location-12345", "order-id")

        assert "Phase 4" in str(exc_info.value)


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestSquareProtocolCompliance:
    """Tests for POSAdapter protocol compliance."""

    def test_provider_property(self, adapter):
        """Test that provider property returns SQUARE."""
        assert adapter.provider == POSProvider.SQUARE

    def test_adapter_implements_protocol(self, adapter):
        """Test that SquareAdapter implements POSAdapter protocol."""
        assert isinstance(adapter, POSAdapter)


# =============================================================================
# Adapter Registry Tests
# =============================================================================


class TestSquareAdapterRegistry:
    """Tests for the adapter factory/registry with Square."""

    def test_get_square_adapter(self):
        """Test getting Square adapter from registry."""
        adapter = get_adapter(POSProvider.SQUARE)

        assert isinstance(adapter, SquareAdapter)
        assert adapter.provider == POSProvider.SQUARE

    def test_get_square_adapter_sandbox(self):
        """Test getting Square adapter in sandbox mode."""
        adapter = get_adapter(POSProvider.SQUARE, sandbox=True)

        assert isinstance(adapter, SquareAdapter)
        assert adapter._sandbox is True
        assert adapter._base_url == SquareAdapter.SANDBOX_BASE_URL

    def test_get_square_adapter_production(self):
        """Test getting Square adapter in production mode."""
        adapter = get_adapter(POSProvider.SQUARE, sandbox=False)

        assert isinstance(adapter, SquareAdapter)
        assert adapter._sandbox is False
        assert adapter._base_url == SquareAdapter.PROD_BASE_URL


# =============================================================================
# Environment Switching Tests
# =============================================================================


class TestSquareEnvironments:
    """Tests for sandbox vs production environment switching."""

    def test_sandbox_base_url(self):
        """Test that sandbox mode uses correct base URL."""
        adapter = SquareAdapter(sandbox=True)
        assert adapter._base_url == "https://connect.squareupsandbox.com"

    def test_production_base_url(self):
        """Test that production mode uses correct base URL."""
        adapter = SquareAdapter(sandbox=False)
        assert adapter._base_url == "https://connect.squareup.com"

    def test_default_is_production(self):
        """Test that default is production mode."""
        adapter = SquareAdapter()
        assert adapter._sandbox is False
        assert adapter._base_url == "https://connect.squareup.com"
