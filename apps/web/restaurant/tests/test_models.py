"""Tests for restaurant models."""

from decimal import Decimal

from django.db import IntegrityError

import pytest

from apps.web.restaurant.models import (
    Menu,
    OrderStatus,
    OrderType,
    PaymentStatus,
)

from .factories import (
    ClientFactory,
    MenuCategoryFactory,
    MenuFactory,
    MenuItemFactory,
    ModifierFactory,
    ModifierGroupFactory,
    OrderFactory,
    OrderItemFactory,
    RestaurantProfileFactory,
)


@pytest.mark.django_db
class TestRestaurantProfile:
    """Tests for RestaurantProfile model."""

    def test_create_profile(self) -> None:
        """Test creating a restaurant profile."""
        profile = RestaurantProfileFactory()

        assert profile.pk is not None
        assert profile.client is not None
        assert profile.ordering_enabled is True

    def test_has_pos_false_when_no_provider(self) -> None:
        """Test has_pos returns False when no POS configured."""
        profile = RestaurantProfileFactory(pos_provider="", pos_location_id="")

        assert profile.has_pos is False

    def test_has_pos_true_when_configured(self) -> None:
        """Test has_pos returns True when POS is configured."""
        profile = RestaurantProfileFactory(
            pos_provider="toast", pos_location_id="loc-123"
        )

        assert profile.has_pos is True

    def test_unique_profile_per_client(self) -> None:
        """Test that each client can only have one profile."""
        client = ClientFactory()
        RestaurantProfileFactory(client=client)

        # Creating a second profile for the same client should fail
        with pytest.raises(IntegrityError):
            RestaurantProfileFactory(client=client)


@pytest.mark.django_db
class TestMenu:
    """Tests for Menu model."""

    def test_create_menu(self) -> None:
        """Test creating a menu."""
        menu = MenuFactory(name="Dinner", description="Evening specials")

        assert menu.pk is not None
        assert menu.name == "Dinner"
        assert menu.is_active is True

    def test_menu_ordering(self) -> None:
        """Test menus are ordered by display_order."""
        client = ClientFactory()
        menu2 = MenuFactory(client=client, name="Lunch", display_order=2)
        menu1 = MenuFactory(client=client, name="Breakfast", display_order=1)

        menus = list(Menu.objects.filter(client=client))
        assert menus[0] == menu1
        assert menus[1] == menu2


@pytest.mark.django_db
class TestMenuCategory:
    """Tests for MenuCategory model."""

    def test_create_category(self) -> None:
        """Test creating a menu category."""
        category = MenuCategoryFactory(name="Appetizers")

        assert category.pk is not None
        assert category.name == "Appetizers"
        assert category.menu is not None

    def test_category_str(self) -> None:
        """Test category string representation."""
        menu = MenuFactory(name="Dinner")
        category = MenuCategoryFactory(menu=menu, client=menu.client, name="Entrees")

        assert str(category) == "Dinner > Entrees"


@pytest.mark.django_db
class TestMenuItem:
    """Tests for MenuItem model."""

    def test_create_item(self) -> None:
        """Test creating a menu item."""
        item = MenuItemFactory(
            name="Burger",
            price=Decimal("15.99"),
            is_vegetarian=False,
        )

        assert item.pk is not None
        assert item.name == "Burger"
        assert item.price == Decimal("15.99")
        assert item.is_available is True

    def test_item_availability(self) -> None:
        """Test 86'd item availability."""
        item = MenuItemFactory(is_available=False)

        assert item.is_available is False

    def test_dietary_flags(self) -> None:
        """Test dietary information flags."""
        item = MenuItemFactory(
            is_vegetarian=True,
            is_vegan=True,
            is_gluten_free=True,
            allergens=["soy", "sesame"],
        )

        assert item.is_vegetarian is True
        assert item.is_vegan is True
        assert item.is_gluten_free is True
        assert "soy" in item.allergens


@pytest.mark.django_db
class TestModifierGroup:
    """Tests for ModifierGroup model."""

    def test_create_modifier_group(self) -> None:
        """Test creating a modifier group."""
        group = ModifierGroupFactory(
            name="Choose Protein",
            min_selections=1,
            max_selections=1,
        )

        assert group.pk is not None
        assert group.name == "Choose Protein"
        assert group.is_required is True

    def test_optional_modifier_group(self) -> None:
        """Test optional modifier group."""
        group = ModifierGroupFactory(min_selections=0, max_selections=3)

        assert group.is_required is False


@pytest.mark.django_db
class TestModifier:
    """Tests for Modifier model."""

    def test_create_modifier(self) -> None:
        """Test creating a modifier."""
        modifier = ModifierFactory(
            name="Extra Cheese",
            price_adjustment=Decimal("1.50"),
        )

        assert modifier.pk is not None
        assert modifier.name == "Extra Cheese"
        assert modifier.price_adjustment == Decimal("1.50")

    def test_modifier_str_with_price(self) -> None:
        """Test modifier string representation with price."""
        modifier = ModifierFactory(
            name="Add Bacon",
            price_adjustment=Decimal("2.00"),
        )

        assert str(modifier) == "Add Bacon (+$2.00)"

    def test_modifier_str_without_price(self) -> None:
        """Test modifier string representation without price."""
        modifier = ModifierFactory(
            name="No Onions",
            price_adjustment=Decimal("0"),
        )

        assert str(modifier) == "No Onions"


@pytest.mark.django_db
class TestOrder:
    """Tests for Order model."""

    def test_create_order(self) -> None:
        """Test creating an order."""
        order = OrderFactory(
            customer_name="John Doe",
            customer_email="john@example.com",
            order_type=OrderType.PICKUP,
        )

        assert order.pk is not None
        assert order.customer_name == "John Doe"
        assert order.status == OrderStatus.PENDING
        assert order.order_type == OrderType.PICKUP

    def test_order_status_choices(self) -> None:
        """Test order status transitions."""
        order = OrderFactory(status=OrderStatus.CONFIRMED)

        assert order.status == OrderStatus.CONFIRMED

        order.status = OrderStatus.PREPARING
        order.save()

        order.refresh_from_db()
        assert order.status == OrderStatus.PREPARING

    def test_payment_status_choices(self) -> None:
        """Test payment status options."""
        order = OrderFactory(payment_status=PaymentStatus.CAPTURED)

        assert order.payment_status == PaymentStatus.CAPTURED


@pytest.mark.django_db
class TestOrderItem:
    """Tests for OrderItem model."""

    def test_create_order_item(self) -> None:
        """Test creating an order item."""
        order_item = OrderItemFactory(quantity=2)

        assert order_item.pk is not None
        assert order_item.quantity == 2
        assert order_item.order is not None
        assert order_item.menu_item is not None

    def test_order_item_str(self) -> None:
        """Test order item string representation."""
        item = MenuItemFactory(name="Pizza")
        order_item = OrderItemFactory(
            menu_item=item,
            client=item.client,
            item_name="Pizza",
            quantity=2,
        )

        assert str(order_item) == "2x Pizza"


@pytest.mark.django_db
class TestModelRelationships:
    """Tests for model relationships."""

    def test_menu_to_categories(self) -> None:
        """Test menu has categories."""
        menu = MenuFactory()
        cat1 = MenuCategoryFactory(menu=menu, client=menu.client, name="Apps")
        cat2 = MenuCategoryFactory(menu=menu, client=menu.client, name="Mains")

        assert menu.categories.count() == 2
        assert cat1 in menu.categories.all()
        assert cat2 in menu.categories.all()

    def test_category_to_items(self) -> None:
        """Test category has items."""
        category = MenuCategoryFactory()
        item1 = MenuItemFactory(category=category, client=category.client)
        MenuItemFactory(category=category, client=category.client)  # item2

        assert category.items.count() == 2
        assert item1 in category.items.all()

    def test_item_to_modifier_groups(self) -> None:
        """Test item has modifier groups."""
        item = MenuItemFactory()
        group = ModifierGroupFactory(item=item, client=item.client)

        assert item.modifier_groups.count() == 1
        assert group in item.modifier_groups.all()

    def test_modifier_group_to_modifiers(self) -> None:
        """Test modifier group has modifiers."""
        group = ModifierGroupFactory()
        mod1 = ModifierFactory(group=group, client=group.client)
        ModifierFactory(group=group, client=group.client)  # mod2

        assert group.modifiers.count() == 2
        assert mod1 in group.modifiers.all()

    def test_order_to_items(self) -> None:
        """Test order has items."""
        order = OrderFactory()
        item1 = OrderItemFactory(order=order, client=order.client)
        OrderItemFactory(order=order, client=order.client)  # item2

        assert order.items.count() == 2
        assert item1 in order.items.all()
