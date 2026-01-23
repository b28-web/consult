"""Tests for ToastAdapter - comprehensive mocked API tests."""

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

from apps.web.pos.adapters import MockPOSAdapter, get_adapter
from apps.web.pos.adapters.base import POSAdapter
from apps.web.pos.adapters.toast import RateLimiter, ToastAdapter
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
def adapter() -> ToastAdapter:
    """Create a Toast adapter with mocked HTTP client."""
    return ToastAdapter()


@pytest.fixture
def credentials() -> POSCredentials:
    """Create test Toast credentials."""
    return POSCredentials(
        provider=POSProvider.TOAST,
        client_id="toast-client-id",
        client_secret="toast-client-secret",
        location_id="restaurant-guid-12345",
    )


@pytest.fixture
def session() -> POSSession:
    """Create a test Toast session."""
    return POSSession(
        provider=POSProvider.TOAST,
        access_token="toast-access-token-xyz",
        refresh_token=None,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )


@pytest.fixture
def toast_menu_response() -> dict:
    """Sample Toast API menu response matching their actual format."""
    return [
        {
            "guid": "menu-guid-001",
            "name": "Dinner Menu",
            "description": "Evening favorites",
            "availability": {
                "startTime": "17:00:00",
                "endTime": "22:00:00",
            },
            "menuGroups": [
                {
                    "guid": "group-guid-001",
                    "name": "Appetizers",
                    "description": "Start your meal right",
                    "menuItems": [
                        {
                            "guid": "item-guid-001",
                            "name": "Crispy Calamari",
                            "description": "Lightly fried with marinara",
                            "price": 14.99,
                            "imageUrl": "https://cdn.toast.com/calamari.jpg",
                            "visibility": "ALL",
                            "tags": [
                                {"name": "allergen:shellfish"},
                                {"name": "allergen:gluten"},
                            ],
                            "modifierGroups": [
                                {
                                    "guid": "mod-group-001",
                                    "name": "Sauce Choice",
                                    "minSelections": 0,
                                    "maxSelections": 2,
                                    "modifiers": [
                                        {
                                            "guid": "mod-001",
                                            "name": "Extra Marinara",
                                            "price": 1.50,
                                            "visibility": "ALL",
                                        },
                                        {
                                            "guid": "mod-002",
                                            "name": "Aioli",
                                            "price": 2.00,
                                            "visibility": "ALL",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "guid": "item-guid-002",
                            "name": "Garden Salad",
                            "description": "Fresh mixed greens",
                            "price": 9.99,
                            "visibility": "ALL",
                            "tags": [
                                {"name": "vegetarian"},
                                {"name": "vegan"},
                                {"name": "gluten-free"},
                            ],
                            "modifierGroups": [],
                        },
                    ],
                },
                {
                    "guid": "group-guid-002",
                    "name": "Entrees",
                    "description": "Main courses",
                    "menuItems": [
                        {
                            "guid": "item-guid-003",
                            "name": "Grilled Salmon",
                            "description": "Atlantic salmon with lemon butter",
                            "price": 28.99,
                            "visibility": "ALL",
                            "tags": [{"name": "gluten free"}],
                            "modifierGroups": [],
                        },
                        {
                            "guid": "item-guid-004",
                            "name": "Ribeye Steak",
                            "description": "12oz USDA Prime",
                            "price": 45.99,
                            "visibility": "NONE",  # 86'd item
                            "tags": [],
                            "modifierGroups": [],
                        },
                    ],
                },
            ],
        },
    ]


@pytest.fixture
def toast_stock_response() -> dict:
    """Sample Toast stock/inventory API response."""
    return {
        "stockItems": [
            {"guid": "item-guid-001", "outOfStock": False},
            {"guid": "item-guid-002", "outOfStock": False},
            {"guid": "item-guid-003", "outOfStock": False},
            {"guid": "item-guid-004", "outOfStock": True},  # 86'd
        ]
    }


# =============================================================================
# Authentication Tests
# =============================================================================


class TestToastAuthentication:
    """Tests for Toast OAuth authentication."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_success(self, adapter, credentials):
        """Test successful Toast authentication."""
        respx.post(ToastAdapter.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "token": {
                        "accessToken": "toast-token-abc123",
                        "expiresIn": 86400,
                    }
                },
            )
        )

        session = await adapter.authenticate(credentials)

        assert session.provider == POSProvider.TOAST
        assert session.access_token == "toast-token-abc123"
        assert session.refresh_token is None  # Toast doesn't use refresh tokens
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_invalid_credentials(self, adapter, credentials):
        """Test authentication with invalid credentials."""
        respx.post(ToastAdapter.AUTH_URL).mock(
            return_value=httpx.Response(
                401,
                json={"error": "Invalid credentials"},
            )
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "Invalid Toast credentials" in str(exc_info.value)
        assert exc_info.value.provider == "toast"

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_server_error(self, adapter, credentials):
        """Test authentication when Toast API returns server error."""
        respx.post(ToastAdapter.AUTH_URL).mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        with pytest.raises(POSAuthError):
            await adapter.authenticate(credentials)

    @pytest.mark.asyncio
    async def test_refresh_token_not_supported(self, adapter, session):
        """Test that refresh_token raises error (Toast doesn't support it)."""
        with pytest.raises(POSAuthError) as exc_info:
            await adapter.refresh_token(session)

        assert "does not support token refresh" in str(exc_info.value)


# =============================================================================
# Menu Operation Tests
# =============================================================================


class TestToastMenuOperations:
    """Tests for menu fetching from Toast API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menus_success(self, adapter, session, toast_menu_response):
        """Test fetching all menus from Toast."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")

        assert len(menus) == 1
        menu = menus[0]
        assert menu.external_id == "menu-guid-001"
        assert menu.name == "Dinner Menu"
        assert menu.available_start == "17:00"
        assert menu.available_end == "22:00"
        assert len(menu.categories) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_categories_parsed_correctly(
        self, adapter, session, toast_menu_response
    ):
        """Test that menu categories are correctly parsed."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        appetizers = menus[0].categories[0]

        assert appetizers.external_id == "group-guid-001"
        assert appetizers.name == "Appetizers"
        assert len(appetizers.items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_items_parsed_correctly(
        self, adapter, session, toast_menu_response
    ):
        """Test that menu items are correctly parsed with all fields."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        calamari = menus[0].categories[0].items[0]

        assert calamari.external_id == "item-guid-001"
        assert calamari.name == "Crispy Calamari"
        assert calamari.description == "Lightly fried with marinara"
        assert calamari.price == Decimal("14.99")
        assert calamari.image_url == "https://cdn.toast.com/calamari.jpg"
        assert calamari.is_available is True
        assert "shellfish" in calamari.allergens
        assert "gluten" in calamari.allergens

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_item_dietary_flags(self, adapter, session, toast_menu_response):
        """Test that dietary flags are extracted from Toast tags."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        salad = menus[0].categories[0].items[1]

        assert salad.is_vegetarian is True
        assert salad.is_vegan is True
        assert salad.is_gluten_free is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_menu_item_86d_status(self, adapter, session, toast_menu_response):
        """Test that 86'd items (visibility=NONE) are marked unavailable."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        ribeye = menus[0].categories[1].items[1]

        assert ribeye.name == "Ribeye Steak"
        assert ribeye.is_available is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifier_groups_parsed(self, adapter, session, toast_menu_response):
        """Test that modifier groups are correctly parsed."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        calamari = menus[0].categories[0].items[0]

        assert len(calamari.modifier_groups) == 1
        sauce_group = calamari.modifier_groups[0]
        assert sauce_group.name == "Sauce Choice"
        assert sauce_group.min_selections == 0
        assert sauce_group.max_selections == 2
        assert len(sauce_group.modifiers) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_modifiers_parsed(self, adapter, session, toast_menu_response):
        """Test that individual modifiers are correctly parsed."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(200, json=toast_menu_response)
        )

        menus = await adapter.get_menus(session, "restaurant-guid-12345")
        calamari = menus[0].categories[0].items[0]
        aioli = calamari.modifier_groups[0].modifiers[1]

        assert aioli.external_id == "mod-002"
        assert aioli.name == "Aioli"
        assert aioli.price_adjustment == Decimal("2.00")
        assert aioli.is_available is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_menu_by_id(self, adapter, session, toast_menu_response):
        """Test fetching a specific menu by ID."""
        single_menu = toast_menu_response[0]
        respx.get(f"{ToastAdapter.MENUS_URL}/menu-guid-001").mock(
            return_value=httpx.Response(200, json=single_menu)
        )

        menu = await adapter.get_menu(session, "restaurant-guid-12345", "menu-guid-001")

        assert menu.external_id == "menu-guid-001"
        assert menu.name == "Dinner Menu"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_item_availability(self, adapter, session, toast_stock_response):
        """Test fetching item availability from stock API."""
        respx.get(ToastAdapter.STOCK_URL).mock(
            return_value=httpx.Response(200, json=toast_stock_response)
        )

        availability = await adapter.get_item_availability(
            session, "restaurant-guid-12345"
        )

        assert availability["item-guid-001"] is True
        assert availability["item-guid-002"] is True
        assert availability["item-guid-003"] is True
        assert availability["item-guid-004"] is False  # 86'd


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestToastErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_error(self, adapter, session):
        """Test that rate limit errors are handled correctly."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(POSRateLimitError) as exc_info:
            await adapter.get_menus(session, "restaurant-guid-12345")

        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_expired_error(self, adapter, session):
        """Test that expired session triggers auth error."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(401, json={"error": "Token expired"})
        )

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.get_menus(session, "restaurant-guid-12345")

        assert "session expired" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_transient_error(
        self, adapter, session, toast_menu_response
    ):
        """Test that transient errors trigger retries."""
        # First call fails, second succeeds
        route = respx.get(ToastAdapter.MENUS_URL)
        route.side_effect = [
            httpx.Response(503, json={"error": "Service unavailable"}),
            httpx.Response(200, json=toast_menu_response),
        ]

        menus = await adapter.get_menus(session, "restaurant-guid-12345")

        assert len(menus) == 1
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exceeded(self, adapter, session):
        """Test that API error is raised after max retries."""
        respx.get(ToastAdapter.MENUS_URL).mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menus(session, "restaurant-guid-12345")

        assert "after 3 attempts" in str(exc_info.value)


# =============================================================================
# Rate Limiter Tests
# =============================================================================


class TestRateLimiter:
    """Tests for the rate limiter utility."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_first_request(self):
        """Test that first request goes through immediately."""
        limiter = RateLimiter(requests_per_second=1.0)
        start = datetime.now(UTC)
        await limiter.acquire()
        elapsed = (datetime.now(UTC) - start).total_seconds()

        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_rate_limiter_per_location(self, adapter):
        """Test that rate limiters are per-location."""
        limiter1 = adapter._get_rate_limiter("location-1")
        limiter2 = adapter._get_rate_limiter("location-2")

        assert limiter1 is not limiter2

        # Same location returns same limiter
        limiter1_again = adapter._get_rate_limiter("location-1")
        assert limiter1 is limiter1_again


# =============================================================================
# Webhook Tests
# =============================================================================


class TestToastWebhooks:
    """Tests for Toast webhook handling."""

    def test_verify_webhook_signature_valid(self, adapter):
        """Test valid webhook signature verification."""
        payload = b'{"eventType": "MENU_UPDATED", "menuGuid": "menu-001"}'
        secret = "webhook-secret-xyz"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert adapter.verify_webhook_signature(payload, signature, secret) is True

    def test_verify_webhook_signature_invalid(self, adapter):
        """Test invalid webhook signature rejection."""
        payload = b'{"eventType": "MENU_UPDATED"}'
        secret = "webhook-secret-xyz"

        result = adapter.verify_webhook_signature(payload, "invalid-sig", secret)

        assert result is False

    def test_verify_webhook_signature_case_insensitive(self, adapter):
        """Test that signature comparison is case-insensitive."""
        payload = b'{"eventType": "MENU_UPDATED"}'
        secret = "webhook-secret-xyz"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Test uppercase signature
        assert (
            adapter.verify_webhook_signature(payload, signature.upper(), secret) is True
        )

    def test_parse_webhook_menu_updated(self, adapter):
        """Test parsing MENU_UPDATED webhook event."""
        payload = {
            "eventType": "MENU_UPDATED",
            "eventId": "evt-12345",
            "occurredAt": "2026-01-23T15:30:00Z",
            "menuGuid": "menu-guid-001",
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.provider == POSProvider.TOAST
        assert event.event_id == "evt-12345"
        assert event.menu_id == "menu-guid-001"
        assert event.occurred_at.year == 2026

    def test_parse_webhook_item_availability_changed(self, adapter):
        """Test parsing ITEM_AVAILABILITY_CHANGED webhook event."""
        payload = {
            "eventType": "ITEM_AVAILABILITY_CHANGED",
            "eventId": "evt-67890",
            "occurredAt": "2026-01-23T15:45:00Z",
            "itemGuid": "item-guid-004",
            "outOfStock": True,
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.provider == POSProvider.TOAST
        assert event.item_id == "item-guid-004"
        assert event.is_available is False  # outOfStock=True means not available

    def test_parse_webhook_item_back_in_stock(self, adapter):
        """Test parsing webhook when item comes back in stock."""
        payload = {
            "eventType": "ITEM_AVAILABILITY_CHANGED",
            "eventId": "evt-11111",
            "occurredAt": "2026-01-23T16:00:00Z",
            "itemGuid": "item-guid-004",
            "outOfStock": False,
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.is_available is True

    def test_parse_webhook_unknown_event_type(self, adapter):
        """Test parsing unknown webhook event type raises error."""
        payload = {
            "eventType": "UNKNOWN_EVENT",
            "eventId": "evt-00000",
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Unknown Toast webhook event type" in str(exc_info.value)

    def test_parse_webhook_invalid_timestamp(self, adapter):
        """Test parsing webhook with invalid timestamp raises error."""
        payload = {
            "eventType": "MENU_UPDATED",
            "eventId": "evt-12345",
            "occurredAt": "not-a-timestamp",
            "menuGuid": "menu-001",
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Invalid timestamp" in str(exc_info.value)

    def test_parse_webhook_fallback_entity_guid(self, adapter):
        """Test parsing webhook with entityGuid fallback."""
        payload = {
            "eventType": "MENU_UPDATED",
            "eventId": "evt-12345",
            "occurredAt": "2026-01-23T15:30:00Z",
            "entityGuid": "menu-guid-from-entity",  # Fallback field
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.menu_id == "menu-guid-from-entity"


# =============================================================================
# Order Operation Tests (Phase 4 - Not Implemented)
# =============================================================================


class TestToastOrderOperations:
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
            await adapter.create_order(session, "location-id", order)

        assert "Partner API access" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_status_not_implemented(self, adapter, session):
        """Test that order status raises not implemented error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_order_status(session, "location-id", "order-id")

        assert "Partner API access" in str(exc_info.value)


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestToastProtocolCompliance:
    """Tests for POSAdapter protocol compliance."""

    def test_provider_property(self, adapter):
        """Test that provider property returns TOAST."""
        assert adapter.provider == POSProvider.TOAST

    def test_adapter_implements_protocol(self, adapter):
        """Test that ToastAdapter implements POSAdapter protocol."""
        assert isinstance(adapter, POSAdapter)


# =============================================================================
# Adapter Registry Tests
# =============================================================================


class TestAdapterRegistry:
    """Tests for the adapter factory/registry."""

    def test_get_toast_adapter(self):
        """Test getting Toast adapter from registry."""
        adapter = get_adapter(POSProvider.TOAST)

        assert isinstance(adapter, ToastAdapter)
        assert adapter.provider == POSProvider.TOAST

    def test_get_mock_adapter(self):
        """Test getting Mock adapter from registry."""
        adapter = get_adapter(POSProvider.MOCK)

        assert isinstance(adapter, MockPOSAdapter)
        assert adapter.provider == POSProvider.MOCK

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_adapter(POSProvider.SQUARE)

        assert "Unsupported POS provider" in str(exc_info.value)
        assert "SQUARE" in str(exc_info.value)
