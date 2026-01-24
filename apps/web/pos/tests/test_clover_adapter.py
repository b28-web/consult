"""Tests for CloverAdapter - comprehensive mocked API tests."""

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

from apps.web.pos.adapters import CloverAdapter, get_adapter
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
def adapter() -> CloverAdapter:
    """Create a Clover adapter for testing."""
    return CloverAdapter(sandbox=True)


@pytest.fixture
def credentials() -> POSCredentials:
    """Create test Clover credentials."""
    return POSCredentials(
        provider=POSProvider.CLOVER,
        client_id="clover-app-id",
        client_secret="clover-app-secret",
        location_id="merchant-12345",
        extra={"auth_code": "auth-code-xyz"},
    )


@pytest.fixture
def session() -> POSSession:
    """Create a test Clover session."""
    return POSSession(
        provider=POSProvider.CLOVER,
        access_token="clover-access-token-abc",
        refresh_token=None,
        expires_at=datetime.now(UTC) + timedelta(days=365),
    )


@pytest.fixture
def clover_categories_response() -> dict:
    """Sample Clover categories API response."""
    return {
        "elements": [
            {
                "id": "cat-001",
                "name": "Appetizers",
                "sortOrder": 1,
            },
            {
                "id": "cat-002",
                "name": "Entrees",
                "sortOrder": 2,
            },
            {
                "id": "cat-003",
                "name": "Desserts",
                "sortOrder": 3,
            },
        ]
    }


@pytest.fixture
def clover_items_response() -> dict:
    """Sample Clover items API response."""
    return {
        "elements": [
            {
                "id": "item-001",
                "name": "Crispy Calamari",
                "alternateName": "Lightly fried with marinara",
                "price": 1499,  # Clover uses cents
                "hidden": False,
                "categories": {"elements": [{"id": "cat-001"}]},
                "modifierGroups": {
                    "elements": [
                        {
                            "id": "mod-group-001",
                            "name": "Sauce Choice",
                            "minRequired": 0,
                            "maxAllowed": 2,
                            "modifiers": {
                                "elements": [
                                    {
                                        "id": "mod-001",
                                        "name": "Extra Marinara",
                                        "price": 150,
                                        "hidden": False,
                                    },
                                    {
                                        "id": "mod-002",
                                        "name": "Aioli",
                                        "price": 200,
                                        "hidden": False,
                                    },
                                ]
                            },
                        }
                    ]
                },
            },
            {
                "id": "item-002",
                "name": "Garden Salad",
                "alternateName": "Fresh mixed greens",
                "price": 999,
                "hidden": False,
                "categories": {"elements": [{"id": "cat-001"}]},
                "modifierGroups": {"elements": []},
            },
            {
                "id": "item-003",
                "name": "Grilled Salmon",
                "alternateName": "Atlantic salmon with lemon butter",
                "price": 2899,
                "hidden": False,
                "categories": {"elements": [{"id": "cat-002"}]},
                "modifierGroups": {"elements": []},
            },
            {
                "id": "item-004",
                "name": "Ribeye Steak",
                "alternateName": "12oz USDA Prime",
                "price": 4599,
                "hidden": True,  # 86'd item
                "categories": {"elements": [{"id": "cat-002"}]},
                "modifierGroups": {"elements": []},
            },
            {
                "id": "item-005",
                "name": "Special Item",
                "alternateName": "No category item",
                "price": 1299,
                "hidden": False,
                "categories": {"elements": []},  # No category
                "modifierGroups": {"elements": []},
            },
        ]
    }


@pytest.fixture
def clover_stock_response() -> dict:
    """Sample Clover item_stocks API response."""
    return {
        "elements": [
            {"item": {"id": "item-001"}, "quantity": 10, "stockCount": 10},
            {"item": {"id": "item-002"}, "quantity": 5, "stockCount": 5},
            # Out of stock
            {"item": {"id": "item-003"}, "quantity": 0, "stockCount": 0},
            # No tracking
            {"item": {"id": "item-004"}, "quantity": 3, "stockCount": None},
        ]
    }


# =============================================================================
# Authentication Tests
# =============================================================================


class TestCloverAuthentication:
    """Tests for Clover OAuth authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_success(self, adapter, credentials):
        """Test successful Clover authentication."""
        respx.post(f"{adapter._base_url}/oauth/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "clover-token-abc123",
                    "merchant_id": "merchant-12345",
                },
            )
        )

        session = await adapter.authenticate(credentials)

        assert session.provider == POSProvider.CLOVER
        assert session.access_token == "clover-token-abc123"
        assert session.refresh_token is None  # Clover doesn't use refresh tokens
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_authenticate_missing_auth_code(self, adapter):
        """Test authentication fails without auth_code."""
        credentials = POSCredentials(
            provider=POSProvider.CLOVER,
            client_id="clover-app-id",
            client_secret="clover-app-secret",
            location_id="merchant-12345",
            extra={},  # No auth_code
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "auth_code" in str(exc_info.value)
        assert exc_info.value.provider == "clover"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_invalid_credentials(self, adapter, credentials):
        """Test authentication with invalid credentials."""
        respx.post(f"{adapter._base_url}/oauth/token").mock(
            return_value=httpx.Response(
                401,
                json={"error": "Invalid credentials"},
            )
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "Invalid Clover credentials" in str(exc_info.value)
        assert exc_info.value.provider == "clover"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_server_error(self, adapter, credentials):
        """Test authentication when Clover API returns server error."""
        respx.post(f"{adapter._base_url}/oauth/token").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        with pytest.raises(POSAuthError):
            await adapter.authenticate(credentials)

    @pytest.mark.asyncio
    async def test_refresh_token_returns_same_session(self, adapter, session):
        """Test that refresh_token returns same session (tokens don't expire)."""
        refreshed = await adapter.refresh_token(session)

        assert refreshed == session


# =============================================================================
# Menu Operation Tests
# =============================================================================


class TestCloverMenuOperations:
    """Tests for menu fetching from Clover API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menus_success(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test fetching all menus from Clover."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")

        assert len(menus) == 1  # Clover has single menu concept
        menu = menus[0]
        assert menu.external_id == "main"
        assert menu.name == "Menu"
        # 3 categories + 1 for uncategorized items
        assert len(menu.categories) == 4

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_categories_parsed_correctly(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that menu categories are correctly parsed."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        appetizers = menus[0].categories[0]

        assert appetizers.external_id == "cat-001"
        assert appetizers.name == "Appetizers"
        assert len(appetizers.items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_items_parsed_correctly(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that menu items are correctly parsed with all fields."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        calamari = menus[0].categories[0].items[0]

        assert calamari.external_id == "item-001"
        assert calamari.name == "Crispy Calamari"
        assert calamari.description == "Lightly fried with marinara"
        assert calamari.price == Decimal("14.99")  # Converted from cents
        assert calamari.is_available is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_item_86d_status(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that 86'd items (hidden=True) are marked unavailable."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        entrees = menus[0].categories[1]  # Second category
        ribeye = next(i for i in entrees.items if i.name == "Ribeye Steak")

        assert ribeye.is_available is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_uncategorized_items_grouped(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that items without categories are grouped in 'Other Items'."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        other_category = menus[0].categories[-1]  # Last category

        assert other_category.external_id == "uncategorized"
        assert other_category.name == "Other Items"
        assert len(other_category.items) == 1
        assert other_category.items[0].name == "Special Item"

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifier_groups_parsed(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that modifier groups are correctly parsed."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        calamari = menus[0].categories[0].items[0]

        assert len(calamari.modifier_groups) == 1
        sauce_group = calamari.modifier_groups[0]
        assert sauce_group.name == "Sauce Choice"
        assert sauce_group.min_selections == 0
        assert sauce_group.max_selections == 2
        assert len(sauce_group.modifiers) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifiers_parsed(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that individual modifiers are correctly parsed."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")
        calamari = menus[0].categories[0].items[0]
        aioli = calamari.modifier_groups[0].modifiers[1]

        assert aioli.external_id == "mod-002"
        assert aioli.name == "Aioli"
        assert aioli.price_adjustment == Decimal("2.00")  # Converted from cents
        assert aioli.is_available is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menu_by_id_main(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test fetching the main menu by ID."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(200, json=clover_categories_response)
        )

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menu = await adapter.get_menu(session, "merchant-12345", "main")

        assert menu.external_id == "main"
        assert menu.name == "Menu"

    @pytest.mark.asyncio
    async def test_get_menu_by_id_not_found(self, adapter, session):
        """Test fetching a non-existent menu ID raises error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menu(session, "merchant-12345", "nonexistent")

        assert "Menu not found" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_item_availability(self, adapter, session, clover_stock_response):
        """Test fetching item availability from stock API."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/item_stocks").mock(
            return_value=httpx.Response(200, json=clover_stock_response)
        )

        availability = await adapter.get_item_availability(session, "merchant-12345")

        assert availability["item-001"] is True  # quantity > 0
        assert availability["item-002"] is True  # quantity > 0
        assert availability["item-003"] is False  # quantity = 0
        assert availability["item-004"] is True  # No tracking (stockCount = None)


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCloverErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_error(self, adapter, session):
        """Test that rate limit errors are handled correctly."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(POSRateLimitError) as exc_info:
            await adapter.get_menus(session, "merchant-12345")

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_invalid_error(self, adapter, session):
        """Test that invalid session triggers auth error."""
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(401, json={"error": "Invalid token"})
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.get_menus(session, "merchant-12345")

        assert "session invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_transient_error(
        self, adapter, session, clover_categories_response, clover_items_response
    ):
        """Test that transient errors trigger retries."""
        # Categories: first fails, second succeeds
        cat_route = respx.get(
            f"{adapter._base_url}/v3/merchants/merchant-12345/categories"
        )
        cat_route.side_effect = [
            httpx.Response(503, json={"error": "Service unavailable"}),
            httpx.Response(200, json=clover_categories_response),
        ]

        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(200, json=clover_items_response)
        )

        menus = await adapter.get_menus(session, "merchant-12345")

        assert len(menus) == 1
        assert cat_route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exceeded(self, adapter, session):
        """Test that API error is raised after max retries."""
        # Mock both endpoints that get_menus() calls in parallel
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/categories").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )
        respx.get(f"{adapter._base_url}/v3/merchants/merchant-12345/items").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menus(session, "merchant-12345")

        assert "after 3 attempts" in str(exc_info.value)


# =============================================================================
# Webhook Tests
# =============================================================================


class TestCloverWebhooks:
    """Tests for Clover webhook handling."""

    def test_verify_webhook_signature_valid(self, adapter):
        """Test valid webhook signature verification."""
        payload = b'{"merchants": {"merchant-123": {"ITEM": []}}}'
        secret = "webhook-secret-xyz"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert adapter.verify_webhook_signature(payload, signature, secret) is True

    def test_verify_webhook_signature_invalid(self, adapter):
        """Test invalid webhook signature rejection."""
        payload = b'{"merchants": {}}'
        secret = "webhook-secret-xyz"

        result = adapter.verify_webhook_signature(payload, "invalid-sig", secret)

        assert result is False

    def test_verify_webhook_signature_case_insensitive(self, adapter):
        """Test that signature comparison is case-insensitive."""
        payload = b'{"merchants": {}}'
        secret = "webhook-secret-xyz"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Test uppercase signature
        assert (
            adapter.verify_webhook_signature(payload, signature.upper(), secret) is True
        )

    def test_parse_webhook_item_updated(self, adapter):
        """Test parsing ITEM update webhook event."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,  # 2024-01-23 12:00:00 UTC
            "merchants": {
                "merchant-123": {
                    "ITEM": [
                        {
                            "objectId": "item-001",
                            "type": "UPDATE",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.provider == POSProvider.CLOVER
        assert event.menu_id == "main"

    def test_parse_webhook_item_deleted(self, adapter):
        """Test parsing ITEM delete webhook event."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,
            "merchants": {
                "merchant-123": {
                    "ITEM": [
                        {
                            "objectId": "item-001",
                            "type": "DELETE",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.provider == POSProvider.CLOVER
        assert event.item_id == "item-001"
        assert event.is_available is False

    def test_parse_webhook_inventory_updated(self, adapter):
        """Test parsing inventory update webhook event."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,
            "merchants": {
                "merchant-123": {
                    "I": [
                        {
                            "objectId": "item-002",
                            "type": "UPDATE",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.provider == POSProvider.CLOVER
        assert event.item_id == "item-002"
        assert event.is_available is True

    def test_parse_webhook_category_updated(self, adapter):
        """Test parsing category update webhook event."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,
            "merchants": {
                "merchant-123": {
                    "CATEGORY": [
                        {
                            "objectId": "cat-001",
                            "type": "UPDATE",
                        }
                    ]
                }
            },
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.provider == POSProvider.CLOVER
        assert event.menu_id == "main"

    def test_parse_webhook_missing_merchants(self, adapter):
        """Test parsing webhook without merchants data raises error."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "missing merchants data" in str(exc_info.value)

    def test_parse_webhook_unknown_event_type(self, adapter):
        """Test parsing unknown webhook event type raises error."""
        payload = {
            "appId": "app-12345",
            "ts": 1706025600000,
            "merchants": {"merchant-123": {"UNKNOWN_TYPE": [{"objectId": "obj-001"}]}},
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Unknown Clover webhook event type" in str(exc_info.value)


# =============================================================================
# Order Operation Tests (Phase 4 - Not Implemented)
# =============================================================================


class TestCloverOrderOperations:
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
            await adapter.create_order(session, "merchant-12345", order)

        assert "Phase 4" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_status_not_implemented(self, adapter, session):
        """Test that order status raises not implemented error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_order_status(session, "merchant-12345", "order-id")

        assert "Phase 4" in str(exc_info.value)


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestCloverProtocolCompliance:
    """Tests for POSAdapter protocol compliance."""

    def test_provider_property(self, adapter):
        """Test that provider property returns CLOVER."""
        assert adapter.provider == POSProvider.CLOVER

    def test_adapter_implements_protocol(self, adapter):
        """Test that CloverAdapter implements POSAdapter protocol."""
        assert isinstance(adapter, POSAdapter)


# =============================================================================
# Adapter Registry Tests
# =============================================================================


class TestCloverAdapterRegistry:
    """Tests for the adapter factory/registry with Clover."""

    def test_get_clover_adapter(self):
        """Test getting Clover adapter from registry."""
        adapter = get_adapter(POSProvider.CLOVER)

        assert isinstance(adapter, CloverAdapter)
        assert adapter.provider == POSProvider.CLOVER

    def test_get_clover_adapter_sandbox(self):
        """Test getting Clover adapter in sandbox mode."""
        adapter = get_adapter(POSProvider.CLOVER, sandbox=True)

        assert isinstance(adapter, CloverAdapter)
        assert adapter._sandbox is True
        assert adapter._base_url == CloverAdapter.SANDBOX_BASE_URL

    def test_get_clover_adapter_production(self):
        """Test getting Clover adapter in production mode."""
        adapter = get_adapter(POSProvider.CLOVER, sandbox=False)

        assert isinstance(adapter, CloverAdapter)
        assert adapter._sandbox is False
        assert adapter._base_url == CloverAdapter.PROD_BASE_URL


# =============================================================================
# Environment Switching Tests
# =============================================================================


class TestCloverEnvironments:
    """Tests for sandbox vs production environment switching."""

    def test_sandbox_base_url(self):
        """Test that sandbox mode uses correct base URL."""
        adapter = CloverAdapter(sandbox=True)
        assert adapter._base_url == "https://sandbox.dev.clover.com"

    def test_production_base_url(self):
        """Test that production mode uses correct base URL."""
        adapter = CloverAdapter(sandbox=False)
        assert adapter._base_url == "https://api.clover.com"

    def test_default_is_production(self):
        """Test that default is production mode."""
        adapter = CloverAdapter()
        assert adapter._sandbox is False
        assert adapter._base_url == "https://api.clover.com"
