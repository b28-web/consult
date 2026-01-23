"""Tests for MockPOSAdapter."""

import hashlib
import hmac
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from consult_schemas import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderStatus,
    OrderStatusChangedEvent,
    OrderType,
    POSCredentials,
    POSMenu,
    POSOrder,
    POSOrderItem,
    POSProvider,
    POSSession,
)

from apps.web.pos.adapters.mock import MockPOSAdapter
from apps.web.pos.exceptions import (
    POSAPIError,
    POSAuthError,
    POSOrderError,
    POSWebhookError,
)


@pytest.fixture
def adapter() -> MockPOSAdapter:
    """Create a default mock adapter."""
    return MockPOSAdapter()


@pytest.fixture
def credentials() -> POSCredentials:
    """Create test credentials."""
    return POSCredentials(
        provider=POSProvider.MOCK,
        client_id="test-client",
        client_secret="test-secret",
        location_id="test-location",
    )


@pytest.fixture
def session() -> POSSession:
    """Create a test session."""
    return POSSession(
        provider=POSProvider.MOCK,
        access_token="test-token",
        refresh_token="test-refresh",
        expires_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_order() -> POSOrder:
    """Create a sample order for testing."""
    return POSOrder(
        customer_name="Test Customer",
        customer_email="test@example.com",
        customer_phone="555-1234",
        order_type=OrderType.PICKUP,
        special_instructions="Extra napkins",
        items=[
            POSOrderItem(
                menu_item_external_id="item-scrambled",
                name="Scrambled Eggs",
                quantity=2,
                unit_price=Decimal("8.99"),
            ),
        ],
        subtotal=Decimal("17.98"),
        tax=Decimal("1.44"),
        total=Decimal("19.42"),
    )


class TestMockPOSAdapterAuthentication:
    """Tests for authentication methods."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, adapter, credentials):
        """Test successful authentication."""
        session = await adapter.authenticate(credentials)

        assert session.provider == POSProvider.MOCK
        assert session.access_token.startswith("mock-token-")
        assert session.refresh_token.startswith("mock-refresh-")
        assert session.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, credentials):
        """Test authentication failure when configured."""
        adapter = MockPOSAdapter(fail_auth=True)

        with pytest.raises(POSAuthError) as exc_info:
            await adapter.authenticate(credentials)

        assert "Mock authentication failure" in str(exc_info.value)
        assert exc_info.value.provider == "mock"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, adapter, session):
        """Test successful token refresh."""
        new_session = await adapter.refresh_token(session)

        assert new_session.provider == POSProvider.MOCK
        assert new_session.access_token != session.access_token
        assert new_session.refresh_token == session.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, session):
        """Test token refresh failure when configured."""
        adapter = MockPOSAdapter(fail_auth=True)

        with pytest.raises(POSAuthError):
            await adapter.refresh_token(session)


class TestMockPOSAdapterMenuOperations:
    """Tests for menu operations."""

    @pytest.mark.asyncio
    async def test_get_menus_returns_default_menus(self, adapter, session):
        """Test that get_menus returns default test menus."""
        menus = await adapter.get_menus(session, "test-location")

        assert len(menus) == 2
        assert menus[0].name == "Breakfast"
        assert menus[1].name == "Lunch"

    @pytest.mark.asyncio
    async def test_get_menus_with_custom_menus(self, session):
        """Test get_menus with custom menu configuration."""
        custom_menu = POSMenu(
            external_id="custom-menu",
            name="Custom Menu",
            categories=[],
        )
        adapter = MockPOSAdapter(menus=[custom_menu])

        menus = await adapter.get_menus(session, "test-location")

        assert len(menus) == 1
        assert menus[0].name == "Custom Menu"

    @pytest.mark.asyncio
    async def test_get_menu_by_id(self, adapter, session):
        """Test fetching a specific menu by ID."""
        menu = await adapter.get_menu(session, "test-location", "menu-breakfast")

        assert menu.external_id == "menu-breakfast"
        assert menu.name == "Breakfast"

    @pytest.mark.asyncio
    async def test_get_menu_not_found(self, adapter, session):
        """Test that non-existent menu raises error."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_menu(session, "test-location", "nonexistent-menu")

        assert exc_info.value.status_code == 404
        assert "Menu not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_item_availability(self, adapter, session):
        """Test getting item availability."""
        availability = await adapter.get_item_availability(session, "test-location")

        assert "item-scrambled" in availability
        assert availability["item-scrambled"] is True

    @pytest.mark.asyncio
    async def test_unavailable_items_reflected_in_menus(self, session):
        """Test that unavailable items are marked correctly in menus."""
        adapter = MockPOSAdapter(unavailable_items={"item-scrambled"})

        menus = await adapter.get_menus(session, "test-location")
        breakfast = menus[0]
        eggs_category = breakfast.categories[0]
        scrambled = next(
            item for item in eggs_category.items if item.external_id == "item-scrambled"
        )

        assert scrambled.is_available is False

    @pytest.mark.asyncio
    async def test_unavailable_items_reflected_in_availability(self, session):
        """Test that unavailable items are reflected in availability check."""
        adapter = MockPOSAdapter(unavailable_items={"item-scrambled"})

        availability = await adapter.get_item_availability(session, "test-location")

        assert availability["item-scrambled"] is False


class TestMockPOSAdapterItemAvailability:
    """Tests for item availability management."""

    def test_set_item_unavailable(self, adapter):
        """Test marking an item as unavailable."""
        adapter.set_item_unavailable("item-pancakes")

        assert "item-pancakes" in adapter._unavailable_items

    def test_set_item_available(self, adapter):
        """Test marking an item as available."""
        adapter.set_item_unavailable("item-pancakes")
        adapter.set_item_available("item-pancakes")

        assert "item-pancakes" not in adapter._unavailable_items


class TestMockPOSAdapterOrderOperations:
    """Tests for order operations."""

    @pytest.mark.asyncio
    async def test_create_order_success(self, adapter, session, sample_order):
        """Test successful order creation."""
        result = await adapter.create_order(session, "test-location", sample_order)

        assert result.external_id.startswith("mock-order-")
        assert result.status == OrderStatus.CONFIRMED
        assert result.estimated_ready_time is not None
        assert result.confirmation_code is not None

    @pytest.mark.asyncio
    async def test_create_order_failure(self, session, sample_order):
        """Test order creation failure when configured."""
        adapter = MockPOSAdapter(fail_orders=True)

        with pytest.raises(POSOrderError) as exc_info:
            await adapter.create_order(session, "test-location", sample_order)

        assert "Mock order creation failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_order_with_unavailable_item(self, session, sample_order):
        """Test order creation fails for unavailable items."""
        adapter = MockPOSAdapter(unavailable_items={"item-scrambled"})

        with pytest.raises(POSOrderError) as exc_info:
            await adapter.create_order(session, "test-location", sample_order)

        assert "Item is unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_status(self, adapter, session, sample_order):
        """Test getting order status after creation."""
        result = await adapter.create_order(session, "test-location", sample_order)
        status = await adapter.get_order_status(
            session, "test-location", result.external_id
        )

        assert status.external_id == result.external_id
        assert status.status == OrderStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_get_order_status_not_found(self, adapter, session):
        """Test getting status for non-existent order."""
        with pytest.raises(POSAPIError) as exc_info:
            await adapter.get_order_status(
                session, "test-location", "nonexistent-order"
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_set_order_status(self, adapter, session, sample_order):
        """Test manually setting order status."""
        result = await adapter.create_order(session, "test-location", sample_order)
        adapter.set_order_status(result.external_id, OrderStatus.READY)

        status = await adapter.get_order_status(
            session, "test-location", result.external_id
        )

        assert status.status == OrderStatus.READY


class TestMockPOSAdapterWebhooks:
    """Tests for webhook handling."""

    def test_verify_webhook_signature_valid(self, adapter):
        """Test valid webhook signature verification."""
        payload = b'{"event_type": "menu_updated"}'
        secret = "test-secret"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert adapter.verify_webhook_signature(payload, signature, secret) is True

    def test_verify_webhook_signature_invalid(self, adapter):
        """Test invalid webhook signature rejection."""
        payload = b'{"event_type": "menu_updated"}'
        secret = "test-secret"

        assert (
            adapter.verify_webhook_signature(payload, "invalid-signature", secret)
            is False
        )

    def test_parse_webhook_menu_updated(self, adapter):
        """Test parsing menu_updated webhook."""
        payload = {
            "event_type": "menu_updated",
            "event_id": "evt-123",
            "occurred_at": "2026-01-23T10:00:00+00:00",
            "menu_id": "menu-breakfast",
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, MenuUpdatedEvent)
        assert event.menu_id == "menu-breakfast"
        assert event.provider == POSProvider.MOCK

    def test_parse_webhook_item_availability_changed(self, adapter):
        """Test parsing item_availability_changed webhook."""
        payload = {
            "event_type": "item_availability_changed",
            "event_id": "evt-456",
            "occurred_at": "2026-01-23T10:00:00+00:00",
            "item_id": "item-scrambled",
            "is_available": False,
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, ItemAvailabilityChangedEvent)
        assert event.item_id == "item-scrambled"
        assert event.is_available is False

    def test_parse_webhook_order_status_changed(self, adapter):
        """Test parsing order_status_changed webhook."""
        payload = {
            "event_type": "order_status_changed",
            "event_id": "evt-789",
            "occurred_at": "2026-01-23T10:00:00+00:00",
            "order_id": "order-123",
            "status": "ready",
            "previous_status": "preparing",
        }

        event = adapter.parse_webhook(payload)

        assert isinstance(event, OrderStatusChangedEvent)
        assert event.order_id == "order-123"
        assert event.status == OrderStatus.READY
        assert event.previous_status == OrderStatus.PREPARING

    def test_parse_webhook_unknown_event_type(self, adapter):
        """Test parsing unknown event type raises error."""
        payload = {
            "event_type": "unknown_event",
            "event_id": "evt-000",
        }

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Unknown event type" in str(exc_info.value)

    def test_parse_webhook_missing_event_type(self, adapter):
        """Test parsing payload without event_type raises error."""
        payload = {"event_id": "evt-000"}

        with pytest.raises(POSWebhookError) as exc_info:
            adapter.parse_webhook(payload)

        assert "Missing event_type" in str(exc_info.value)


class TestMockPOSAdapterProtocol:
    """Tests for protocol compliance."""

    def test_provider_property(self, adapter):
        """Test that provider property returns MOCK."""
        assert adapter.provider == POSProvider.MOCK
