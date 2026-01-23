"""Factory classes for restaurant models."""

from decimal import Decimal

import factory

from apps.web.core.models import Client
from apps.web.restaurant.models import (
    Menu,
    MenuCategory,
    MenuItem,
    Modifier,
    ModifierGroup,
    Order,
    OrderItem,
    OrderStatus,
    OrderType,
    PaymentStatus,
    RestaurantProfile,
)


class ClientFactory(factory.django.DjangoModelFactory):
    """Factory for Client model."""

    class Meta:
        model = Client

    slug = factory.Sequence(lambda n: f"restaurant-{n}")
    name = factory.Sequence(lambda n: f"Restaurant {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.slug}@example.com")
    vertical = "restaurant"


class RestaurantProfileFactory(factory.django.DjangoModelFactory):
    """Factory for RestaurantProfile model."""

    class Meta:
        model = RestaurantProfile

    client = factory.SubFactory(ClientFactory)
    pos_provider = ""
    pos_location_id = ""
    ordering_enabled = True
    pickup_enabled = True
    delivery_enabled = False
    tax_rate = Decimal("0.0825")


class MenuFactory(factory.django.DjangoModelFactory):
    """Factory for Menu model."""

    class Meta:
        model = Menu

    client = factory.SubFactory(ClientFactory)
    name = factory.Sequence(lambda n: f"Menu {n}")
    description = factory.Faker("sentence")
    is_active = True
    display_order = factory.Sequence(lambda n: n)


class MenuCategoryFactory(factory.django.DjangoModelFactory):
    """Factory for MenuCategory model."""

    class Meta:
        model = MenuCategory

    client = factory.SubFactory(ClientFactory)
    menu = factory.SubFactory(MenuFactory, client=factory.SelfAttribute("..client"))
    name = factory.Sequence(lambda n: f"Category {n}")
    description = factory.Faker("sentence")
    display_order = factory.Sequence(lambda n: n)


class MenuItemFactory(factory.django.DjangoModelFactory):
    """Factory for MenuItem model."""

    class Meta:
        model = MenuItem

    client = factory.SubFactory(ClientFactory)
    category = factory.SubFactory(
        MenuCategoryFactory, client=factory.SelfAttribute("..client")
    )
    name = factory.Sequence(lambda n: f"Item {n}")
    description = factory.Faker("sentence")
    price = factory.LazyFunction(lambda: Decimal("12.99"))
    is_available = True
    display_order = factory.Sequence(lambda n: n)


class ModifierGroupFactory(factory.django.DjangoModelFactory):
    """Factory for ModifierGroup model."""

    class Meta:
        model = ModifierGroup

    client = factory.SubFactory(ClientFactory)
    item = factory.SubFactory(MenuItemFactory, client=factory.SelfAttribute("..client"))
    name = factory.Sequence(lambda n: f"Modifier Group {n}")
    min_selections = 0
    max_selections = 1
    display_order = factory.Sequence(lambda n: n)


class ModifierFactory(factory.django.DjangoModelFactory):
    """Factory for Modifier model."""

    class Meta:
        model = Modifier

    client = factory.SubFactory(ClientFactory)
    group = factory.SubFactory(
        ModifierGroupFactory, client=factory.SelfAttribute("..client")
    )
    name = factory.Sequence(lambda n: f"Modifier {n}")
    price_adjustment = Decimal("0.00")
    is_available = True
    display_order = factory.Sequence(lambda n: n)


class OrderFactory(factory.django.DjangoModelFactory):
    """Factory for Order model."""

    class Meta:
        model = Order

    client = factory.SubFactory(ClientFactory)
    customer_name = factory.Faker("name")
    customer_email = factory.Faker("email")
    customer_phone = factory.Faker("phone_number")
    status = OrderStatus.PENDING
    order_type = OrderType.PICKUP
    subtotal = factory.LazyFunction(lambda: Decimal("25.00"))
    tax = factory.LazyFunction(lambda: Decimal("2.06"))
    total = factory.LazyFunction(lambda: Decimal("27.06"))
    payment_status = PaymentStatus.PENDING
    confirmation_code = factory.Sequence(lambda n: f"ORD{n:06d}")


class OrderItemFactory(factory.django.DjangoModelFactory):
    """Factory for OrderItem model."""

    class Meta:
        model = OrderItem

    client = factory.SubFactory(ClientFactory)
    order = factory.SubFactory(OrderFactory, client=factory.SelfAttribute("..client"))
    menu_item = factory.SubFactory(
        MenuItemFactory, client=factory.SelfAttribute("..client")
    )
    item_name = factory.LazyAttribute(lambda obj: obj.menu_item.name)
    quantity = 1
    unit_price = factory.LazyAttribute(lambda obj: obj.menu_item.price)
    line_total = factory.LazyAttribute(lambda obj: obj.unit_price * obj.quantity)
