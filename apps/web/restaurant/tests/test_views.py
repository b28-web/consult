"""
Integration tests for restaurant API views.
"""

import uuid
from datetime import time
from decimal import Decimal

from django.test import Client as DjangoClient

import pytest

from apps.web.restaurant.models import RestaurantProfile
from apps.web.restaurant.tests.factories import (
    ClientFactory,
    MenuCategoryFactory,
    MenuFactory,
    MenuItemFactory,
    ModifierFactory,
    ModifierGroupFactory,
    RestaurantProfileFactory,
)


@pytest.fixture
def api_client() -> DjangoClient:
    """Django test client for API requests."""
    return DjangoClient()


@pytest.fixture
def restaurant_client():
    """A restaurant client with profile."""
    client = ClientFactory(slug="tonys-pizza", vertical="restaurant")
    RestaurantProfileFactory(client=client)
    return client


@pytest.fixture
def restaurant_with_menu(restaurant_client):
    """A restaurant with a full menu structure."""
    # Create menu
    menu = MenuFactory(
        client=restaurant_client,
        name="Dinner",
        description="Evening menu",
    )

    # Create category
    appetizers = MenuCategoryFactory(
        client=restaurant_client,
        menu=menu,
        name="Appetizers",
        description="Start your meal",
    )

    # Create menu item
    bruschetta = MenuItemFactory(
        client=restaurant_client,
        category=appetizers,
        name="Bruschetta",
        description="Toasted bread with tomatoes",
        price=Decimal("12.99"),
        is_vegetarian=True,
        allergens=["gluten"],
    )

    # Create modifier group
    bread_choice = ModifierGroupFactory(
        client=restaurant_client,
        item=bruschetta,
        name="Bread Choice",
        min_selections=1,
        max_selections=1,
    )

    # Create modifiers
    ModifierFactory(
        client=restaurant_client,
        group=bread_choice,
        name="Sourdough",
        price_adjustment=Decimal("0.00"),
    )
    ModifierFactory(
        client=restaurant_client,
        group=bread_choice,
        name="Ciabatta",
        price_adjustment=Decimal("1.00"),
    )

    return {
        "client": restaurant_client,
        "menu": menu,
        "category": appetizers,
        "item": bruschetta,
        "modifier_group": bread_choice,
    }


@pytest.mark.django_db
class TestMenuListView:
    """Tests for GET /api/clients/{slug}/menu."""

    def test_menu_list_returns_full_structure(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Menu list returns nested menu structure."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/menu")

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "menus" in data
        assert "source" in data
        assert data["source"] == "pos"
        assert len(data["menus"]) == 1

        # Check menu
        menu = data["menus"][0]
        assert menu["name"] == "Dinner"
        assert len(menu["categories"]) == 1

        # Check category
        category = menu["categories"][0]
        assert category["name"] == "Appetizers"
        assert len(category["items"]) == 1

        # Check item
        item = category["items"][0]
        assert item["name"] == "Bruschetta"
        assert item["price"] == "12.99"
        assert item["is_vegetarian"] is True
        assert "gluten" in item["allergens"]

        # Check modifier groups
        assert len(item["modifier_groups"]) == 1
        mod_group = item["modifier_groups"][0]
        assert mod_group["name"] == "Bread Choice"
        assert mod_group["min_selections"] == 1
        assert len(mod_group["modifiers"]) == 2

    def test_menu_list_has_cors_headers(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Menu list response includes CORS headers."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/menu")

        assert response["Access-Control-Allow-Origin"] == "*"
        assert "GET" in response["Access-Control-Allow-Methods"]

    def test_menu_list_has_cache_headers(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Menu list response includes 5-minute cache headers."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/menu")

        assert "max-age=300" in response["Cache-Control"]
        assert "public" in response["Cache-Control"]

    def test_menu_list_404_for_unknown_client(self, api_client: DjangoClient):
        """Menu list returns 404 for unknown client slug."""
        response = api_client.get("/api/clients/nonexistent/menu")

        assert response.status_code == 404

    def test_menu_list_404_when_no_menu_configured(
        self, api_client: DjangoClient, restaurant_client
    ):
        """Menu list returns 404 when no menu exists and no static fallback."""
        response = api_client.get(f"/api/clients/{restaurant_client.slug}/menu")

        assert response.status_code == 404

    def test_menu_list_static_fallback(self, api_client: DjangoClient):
        """Menu list uses static_menu_json when no database menus exist."""
        client = ClientFactory(slug="static-restaurant")
        static_menu = [
            {
                "id": 999,
                "name": "Static Menu",
                "categories": [
                    {
                        "id": 1,
                        "name": "Main",
                        "items": [{"id": 1, "name": "Burger", "price": "10.00"}],
                    }
                ],
            }
        ]
        RestaurantProfileFactory(client=client, static_menu_json=static_menu)

        response = api_client.get(f"/api/clients/{client.slug}/menu")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "static"
        assert data["menus"] == static_menu


@pytest.mark.django_db
class TestMenuDetailView:
    """Tests for GET /api/clients/{slug}/menu/{menu_id}."""

    def test_menu_detail_returns_single_menu(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Menu detail returns a single menu with full structure."""
        slug = restaurant_with_menu["client"].slug
        menu_id = restaurant_with_menu["menu"].pk

        response = api_client.get(f"/api/clients/{slug}/menu/{menu_id}")

        assert response.status_code == 200
        data = response.json()

        assert "menu" in data
        assert data["source"] == "pos"
        assert data["menu"]["name"] == "Dinner"
        assert len(data["menu"]["categories"]) == 1

    def test_menu_detail_404_for_unknown_menu(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Menu detail returns 404 for unknown menu ID."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/menu/99999")

        assert response.status_code == 404

    def test_menu_detail_404_for_other_client_menu(self, api_client: DjangoClient):
        """Menu detail returns 404 when trying to access another client's menu."""
        client1 = ClientFactory(slug="client-1")
        client2 = ClientFactory(slug="client-2")
        menu = MenuFactory(client=client1)

        # Try to access client1's menu via client2's endpoint
        response = api_client.get(f"/api/clients/{client2.slug}/menu/{menu.pk}")

        assert response.status_code == 404

    def test_menu_detail_excludes_inactive_menu(
        self, api_client: DjangoClient, restaurant_client
    ):
        """Menu detail returns 404 for inactive menus."""
        menu = MenuFactory(client=restaurant_client, is_active=False)
        slug = restaurant_client.slug

        response = api_client.get(f"/api/clients/{slug}/menu/{menu.pk}")

        assert response.status_code == 404


@pytest.mark.django_db
class TestAvailabilityView:
    """Tests for GET /api/clients/{slug}/availability."""

    def test_availability_returns_item_status(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Availability endpoint returns item availability map."""
        slug = restaurant_with_menu["client"].slug
        item_id = str(restaurant_with_menu["item"].pk)

        response = api_client.get(f"/api/clients/{slug}/availability")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "modifiers" in data
        assert "as_of" in data
        assert item_id in data["items"]
        assert data["items"][item_id] is True  # Available by default

    def test_availability_reflects_86d_items(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Availability endpoint shows 86'd (unavailable) items."""
        slug = restaurant_with_menu["client"].slug
        item = restaurant_with_menu["item"]

        # 86 the item
        item.is_available = False
        item.save()

        response = api_client.get(f"/api/clients/{slug}/availability")

        data = response.json()
        assert data["items"][str(item.pk)] is False

    def test_availability_includes_modifiers(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Availability endpoint includes modifier availability."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/availability")

        data = response.json()
        # Check that modifiers are included (we created 2 in the fixture)
        assert len(data["modifiers"]) >= 2

    def test_availability_has_short_cache(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Availability endpoint has 30-second cache for frequent polling."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/availability")

        assert "max-age=30" in response["Cache-Control"]
        assert "public" in response["Cache-Control"]

    def test_availability_has_cors_headers(
        self, api_client: DjangoClient, restaurant_with_menu
    ):
        """Availability endpoint includes CORS headers."""
        slug = restaurant_with_menu["client"].slug

        response = api_client.get(f"/api/clients/{slug}/availability")

        assert response["Access-Control-Allow-Origin"] == "*"


@pytest.mark.django_db
class TestMultiTenantIsolation:
    """Tests for multi-tenant data isolation."""

    def test_menus_isolated_by_client(self, api_client: DjangoClient):
        """Each client only sees their own menus."""
        client1 = ClientFactory(slug="client-1")
        client2 = ClientFactory(slug="client-2")

        menu1 = MenuFactory(client=client1, name="Client 1 Menu")
        MenuFactory(client=client2, name="Client 2 Menu")

        response = api_client.get(f"/api/clients/{client1.slug}/menu")

        assert response.status_code == 200
        data = response.json()
        assert len(data["menus"]) == 1
        assert data["menus"][0]["name"] == "Client 1 Menu"
        assert data["menus"][0]["id"] == menu1.pk

    def test_availability_isolated_by_client(self, api_client: DjangoClient):
        """Each client only sees their own item availability."""
        client1 = ClientFactory(slug="avail-client-1")
        client2 = ClientFactory(slug="avail-client-2")

        menu1 = MenuFactory(client=client1)
        category1 = MenuCategoryFactory(client=client1, menu=menu1)
        item1 = MenuItemFactory(client=client1, category=category1)

        menu2 = MenuFactory(client=client2)
        category2 = MenuCategoryFactory(client=client2, menu=menu2)
        item2 = MenuItemFactory(client=client2, category=category2)

        response = api_client.get(f"/api/clients/{client1.slug}/availability")

        data = response.json()
        assert str(item1.pk) in data["items"]
        assert str(item2.pk) not in data["items"]


@pytest.mark.django_db
class TestTimeBasedMenuAvailability:
    """Tests for time-based menu features."""

    def test_menu_includes_availability_times(self, api_client: DjangoClient):
        """Menu response includes time-based availability."""
        client = ClientFactory(slug="timed-menu-client")
        MenuFactory(
            client=client,
            name="Breakfast",
            available_start=time(6, 0),
            available_end=time(11, 0),
        )

        response = api_client.get(f"/api/clients/{client.slug}/menu")

        assert response.status_code == 200
        data = response.json()
        assert data["menus"][0]["available_start"] == "06:00"
        assert data["menus"][0]["available_end"] == "11:00"


# =============================================================================
# Order Endpoint Tests
# =============================================================================


@pytest.fixture
def restaurant_with_ordering(restaurant_with_menu):
    """A restaurant with ordering enabled."""
    # Update the existing profile created by restaurant_client fixture
    profile = RestaurantProfile.objects.get(client=restaurant_with_menu["client"])
    profile.ordering_enabled = True
    profile.pickup_enabled = True
    profile.delivery_enabled = True
    profile.delivery_fee = Decimal("5.00")
    profile.tax_rate = Decimal("0.0825")
    profile.save()

    return {
        **restaurant_with_menu,
        "profile": profile,
    }


@pytest.fixture
def valid_order_payload(restaurant_with_menu):
    """A valid order creation payload."""
    # Get the first modifier from the required modifier group
    modifier_group = restaurant_with_menu["modifier_group"]
    first_modifier = modifier_group.modifiers.first()

    return {
        "customer": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+15555555555",
        },
        "order_type": "pickup",
        "items": [
            {
                "menu_item_id": restaurant_with_menu["item"].pk,
                "quantity": 2,
                "modifiers": [
                    {
                        "group_id": modifier_group.pk,
                        "selections": [first_modifier.pk],
                    }
                ],
                "special_instructions": "Extra crispy",
            }
        ],
        "special_instructions": "Ring doorbell",
        "tip": "5.00",
    }


@pytest.mark.django_db
class TestCreateOrderView:
    """Tests for POST /api/clients/{slug}/orders."""

    def test_create_order_success(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Successful order creation returns order details and Stripe secret."""
        slug = restaurant_with_ordering["client"].slug

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 201
        data = response.json()

        assert "order_id" in data
        assert "confirmation_code" in data
        assert data["confirmation_code"].startswith("ORD-")
        assert data["status"] == "pending"
        assert "stripe_client_secret" in data
        assert data["stripe_client_secret"] is not None

        # Check pricing
        item_price = Decimal("12.99")  # From fixture
        quantity = 2
        expected_subtotal = item_price * quantity
        assert Decimal(data["subtotal"]) == expected_subtotal

    def test_create_order_requires_idempotency_key(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Order creation requires Idempotency-Key header."""
        slug = restaurant_with_ordering["client"].slug

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            # No Idempotency-Key header
        )

        assert response.status_code == 400
        data = response.json()
        assert "Idempotency-Key" in data["error"]

    def test_create_order_idempotency(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Same idempotency key returns cached response."""
        slug = restaurant_with_ordering["client"].slug

        idempotency_key = str(uuid.uuid4())

        # First request
        response1 = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )

        # Second request with same key
        response2 = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )

        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response1.json()["order_id"] == response2.json()["order_id"]

    def test_create_order_validates_unavailable_item(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Order creation fails if item is 86'd."""
        slug = restaurant_with_ordering["client"].slug
        item = restaurant_with_ordering["item"]

        # 86 the item
        item.is_available = False
        item.save()

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert any("unavailable" in d["message"] for d in data["details"])

    def test_create_order_validates_item_exists(
        self, api_client: DjangoClient, restaurant_with_ordering
    ):
        """Order creation fails for non-existent item."""
        slug = restaurant_with_ordering["client"].slug

        payload = {
            "customer": {
                "name": "John Doe",
                "email": "john@example.com",
            },
            "order_type": "pickup",
            "items": [
                {
                    "menu_item_id": 99999,  # Non-existent
                    "quantity": 1,
                }
            ],
        }

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert any("not found" in d["message"] for d in data["details"])

    def test_create_order_validates_modifiers(
        self, api_client: DjangoClient, restaurant_with_ordering
    ):
        """Order creation validates required modifier groups."""
        slug = restaurant_with_ordering["client"].slug
        item = restaurant_with_ordering["item"]
        # Note: modifier_group from fixture has min_selections=1, so it's required
        payload = {
            "customer": {
                "name": "John Doe",
                "email": "john@example.com",
            },
            "order_type": "pickup",
            "items": [
                {
                    "menu_item_id": item.pk,
                    "quantity": 1,
                    "modifiers": [],  # No modifiers - should fail
                }
            ],
        }

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert any("required" in d["message"].lower() for d in data["details"])

    def test_create_order_delivery_requires_address(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Delivery orders require delivery_address."""
        slug = restaurant_with_ordering["client"].slug

        valid_order_payload["order_type"] = "delivery"
        # No delivery_address

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert any("delivery_address" in d["field"] for d in data["details"])

    def test_create_order_has_cors_headers(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Order creation response includes CORS headers."""
        slug = restaurant_with_ordering["client"].slug

        response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response["Access-Control-Allow-Origin"] == "*"
        assert "POST" in response["Access-Control-Allow-Methods"]

    def test_create_order_404_for_unknown_client(
        self, api_client: DjangoClient, valid_order_payload
    ):
        """Order creation returns 404 for unknown client."""

        response = api_client.post(
            "/api/clients/nonexistent/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestGetOrderView:
    """Tests for GET /api/clients/{slug}/orders/{order_id}."""

    def test_get_order_success(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Get order returns full order details."""
        slug = restaurant_with_ordering["client"].slug

        # Create order first
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_id = create_response.json()["order_id"]

        # Get order
        response = api_client.get(f"/api/clients/{slug}/orders/{order_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["order_id"] == order_id
        assert data["customer"]["name"] == "John Doe"
        assert data["customer"]["email"] == "john@example.com"
        assert data["order_type"] == "pickup"
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_get_order_404_for_unknown_order(
        self, api_client: DjangoClient, restaurant_with_ordering
    ):
        """Get order returns 404 for non-existent order."""
        slug = restaurant_with_ordering["client"].slug

        response = api_client.get(f"/api/clients/{slug}/orders/99999")

        assert response.status_code == 404

    def test_get_order_isolation(self, api_client: DjangoClient):
        """Cannot get another client's order."""
        client1 = ClientFactory(slug="order-client-1")
        client2 = ClientFactory(slug="order-client-2")
        RestaurantProfileFactory(client=client1, ordering_enabled=True)

        # Create order for client1
        menu = MenuFactory(client=client1)
        category = MenuCategoryFactory(client=client1, menu=menu)
        item = MenuItemFactory(client=client1, category=category)

        payload = {
            "customer": {"name": "Test", "email": "test@test.com"},
            "order_type": "pickup",
            "items": [{"menu_item_id": item.pk, "quantity": 1}],
        }

        response = api_client.post(
            f"/api/clients/{client1.slug}/orders",
            data=payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_id = response.json()["order_id"]

        # Try to access from client2
        response = api_client.get(f"/api/clients/{client2.slug}/orders/{order_id}")

        assert response.status_code == 404


@pytest.mark.django_db
class TestConfirmOrderView:
    """Tests for POST /api/clients/{slug}/orders/{order_id}/confirm."""

    def test_confirm_order_success(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Confirm order updates status to confirmed."""
        slug = restaurant_with_ordering["client"].slug

        # Create order
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_data = create_response.json()
        order_id = order_data["order_id"]
        payment_intent_id = order_data["stripe_client_secret"].split("_secret_")[0]

        # Confirm order
        response = api_client.post(
            f"/api/clients/{slug}/orders/{order_id}/confirm",
            data={"payment_intent_id": payment_intent_id},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["estimated_ready_time"] is not None

    def test_confirm_order_wrong_payment_intent(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Confirm order fails with wrong payment intent."""
        slug = restaurant_with_ordering["client"].slug

        # Create order
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_id = create_response.json()["order_id"]

        # Confirm with wrong payment intent
        response = api_client.post(
            f"/api/clients/{slug}/orders/{order_id}/confirm",
            data={"payment_intent_id": "pi_wrong_intent"},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "does not match" in response.json()["error"]

    def test_confirm_order_already_confirmed(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Cannot confirm an already confirmed order."""
        slug = restaurant_with_ordering["client"].slug

        # Create and confirm order
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_data = create_response.json()
        order_id = order_data["order_id"]
        payment_intent_id = order_data["stripe_client_secret"].split("_secret_")[0]

        # First confirm
        api_client.post(
            f"/api/clients/{slug}/orders/{order_id}/confirm",
            data={"payment_intent_id": payment_intent_id},
            content_type="application/json",
        )

        # Second confirm should fail
        response = api_client.post(
            f"/api/clients/{slug}/orders/{order_id}/confirm",
            data={"payment_intent_id": payment_intent_id},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "already" in response.json()["error"].lower()


@pytest.mark.django_db
class TestOrderStatusView:
    """Tests for GET /api/clients/{slug}/orders/{order_id}/status."""

    def test_order_status_success(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Order status returns current status."""
        slug = restaurant_with_ordering["client"].slug

        # Create order
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_id = create_response.json()["order_id"]

        # Get status
        response = api_client.get(f"/api/clients/{slug}/orders/{order_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "updated_at" in data

    def test_order_status_has_short_cache(
        self, api_client: DjangoClient, restaurant_with_ordering, valid_order_payload
    ):
        """Order status has short cache for polling."""
        slug = restaurant_with_ordering["client"].slug

        # Create order
        create_response = api_client.post(
            f"/api/clients/{slug}/orders",
            data=valid_order_payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        order_id = create_response.json()["order_id"]

        # Get status
        response = api_client.get(f"/api/clients/{slug}/orders/{order_id}/status")

        assert "max-age=5" in response["Cache-Control"]

    def test_order_status_404_for_unknown_order(
        self, api_client: DjangoClient, restaurant_with_ordering
    ):
        """Order status returns 404 for non-existent order."""
        slug = restaurant_with_ordering["client"].slug

        response = api_client.get(f"/api/clients/{slug}/orders/99999/status")

        assert response.status_code == 404
