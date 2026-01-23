"""
Integration tests for restaurant API views.
"""

from datetime import time
from decimal import Decimal

from django.test import Client as DjangoClient

import pytest

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
