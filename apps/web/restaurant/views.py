"""
Menu API views - Public endpoints for restaurant menu data.

These endpoints are used by Astro frontends:
- At build time: Full menu fetch for SSG
- At runtime: Availability polling for 86'd items
"""

from datetime import UTC, datetime
from typing import Any

from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.web.core.models import Client
from apps.web.restaurant.models import (
    Menu,
    MenuCategory,
    MenuItem,
    Modifier,
    ModifierGroup,
    RestaurantProfile,
)
from apps.web.restaurant.serializers import (
    AvailabilityResponse,
    MenuCategorySchema,
    MenuItemSchema,
    MenuListResponse,
    MenuSchema,
    ModifierGroupSchema,
    ModifierSchema,
    SingleMenuResponse,
)


def _cors_headers() -> dict[str, str]:
    """CORS headers for Astro site access."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def _json_response(data: dict[str, Any], status: int = 200) -> JsonResponse:
    """Create a JSON response with CORS headers."""
    response = JsonResponse(data, status=status)
    for key, value in _cors_headers().items():
        response[key] = value
    return response


def _serialize_modifier(modifier: Modifier) -> ModifierSchema:
    """Serialize a Modifier model to schema."""
    return ModifierSchema(
        id=modifier.pk,
        name=modifier.name,
        price_adjustment=modifier.price_adjustment,
        is_available=modifier.is_available,
    )


def _serialize_modifier_group(group: ModifierGroup) -> ModifierGroupSchema:
    """Serialize a ModifierGroup model with nested modifiers."""
    modifiers = [
        _serialize_modifier(m) for m in group.modifiers.filter(is_available=True)
    ]
    return ModifierGroupSchema(
        id=group.pk,
        name=group.name,
        min_selections=group.min_selections,
        max_selections=group.max_selections,
        modifiers=modifiers,
    )


def _serialize_menu_item(item: MenuItem) -> MenuItemSchema:
    """Serialize a MenuItem model with nested modifier groups."""
    modifier_groups = [
        _serialize_modifier_group(mg)
        for mg in item.modifier_groups.prefetch_related("modifiers").all()
    ]
    return MenuItemSchema(
        id=item.pk,
        name=item.name,
        description=item.description,
        price=item.price,
        image_url=item.image_url,
        is_available=item.is_available,
        is_vegetarian=item.is_vegetarian,
        is_vegan=item.is_vegan,
        is_gluten_free=item.is_gluten_free,
        allergens=item.allergens,
        modifier_groups=modifier_groups,
    )


def _serialize_category(category: MenuCategory) -> MenuCategorySchema:
    """Serialize a MenuCategory model with nested items."""
    items = [
        _serialize_menu_item(item)
        for item in category.items.prefetch_related(
            "modifier_groups", "modifier_groups__modifiers"
        ).all()
    ]
    return MenuCategorySchema(
        id=category.pk,
        name=category.name,
        description=category.description,
        items=items,
    )


def _serialize_menu(menu: Menu) -> MenuSchema:
    """Serialize a Menu model with nested categories and items."""
    categories = [
        _serialize_category(cat)
        for cat in menu.categories.prefetch_related(
            "items", "items__modifier_groups", "items__modifier_groups__modifiers"
        ).all()
    ]

    available_start = None
    if menu.available_start:
        available_start = menu.available_start.strftime("%H:%M")

    available_end = None
    if menu.available_end:
        available_end = menu.available_end.strftime("%H:%M")

    return MenuSchema(
        id=menu.pk,
        name=menu.name,
        description=menu.description,
        available_start=available_start,
        available_end=available_end,
        categories=categories,
    )


def _get_client_or_404(slug: str) -> Client:
    """Get a client by slug or raise Http404."""
    try:
        return Client.objects.get(slug=slug, is_active=True)
    except Client.DoesNotExist as exc:
        raise Http404(f"Client '{slug}' not found") from exc


def _get_restaurant_profile(client: Client) -> RestaurantProfile | None:
    """Get the restaurant profile for a client, if any."""
    return RestaurantProfile.objects.filter(client=client).first()


@require_GET
@cache_control(max_age=300, public=True)  # 5 minutes
def menu_list(_request: HttpRequest, slug: str) -> JsonResponse:
    """
    GET /api/clients/{slug}/menu

    Returns the full menu structure for a restaurant client.
    Supports static fallback for clients without POS integration.

    Cache: 5 minutes (build-time fetch, not real-time)
    """
    client = _get_client_or_404(slug)
    profile = _get_restaurant_profile(client)

    # Try to get menus from database
    menus = Menu.objects.filter(client=client, is_active=True).prefetch_related(
        "categories",
        "categories__items",
        "categories__items__modifier_groups",
        "categories__items__modifier_groups__modifiers",
    )

    if menus.exists():
        serialized_menus = [_serialize_menu(menu) for menu in menus]
        response = MenuListResponse(
            menus=serialized_menus,
            source="pos",
            last_synced_at=datetime.now(UTC),
        )
        return _json_response(response.model_dump(mode="json"))

    # Static fallback: check for static_menu_json in profile
    if profile and profile.static_menu_json:
        return _json_response(
            {
                "menus": profile.static_menu_json,
                "source": "static",
                "last_synced_at": None,
            }
        )

    # No menu configured
    raise Http404("No menu configured for this restaurant")


@require_GET
@cache_control(max_age=300, public=True)  # 5 minutes
def menu_detail(_request: HttpRequest, slug: str, menu_id: int) -> JsonResponse:
    """
    GET /api/clients/{slug}/menu/{menu_id}

    Returns a single menu with all categories and items.

    Cache: 5 minutes
    """
    client = _get_client_or_404(slug)

    try:
        menu = Menu.objects.prefetch_related(
            "categories",
            "categories__items",
            "categories__items__modifier_groups",
            "categories__items__modifier_groups__modifiers",
        ).get(client=client, pk=menu_id, is_active=True)
    except Menu.DoesNotExist as exc:
        raise Http404(f"Menu {menu_id} not found") from exc

    response = SingleMenuResponse(
        menu=_serialize_menu(menu),
        source="pos",
    )
    return _json_response(response.model_dump(mode="json"))


@require_GET
@cache_control(max_age=30, public=True)  # 30 seconds
def availability(_request: HttpRequest, slug: str) -> JsonResponse:
    """
    GET /api/clients/{slug}/availability

    Returns current availability for all menu items and modifiers.
    Used for real-time 86'd status polling.

    Cache: 30 seconds (frequent polling endpoint)
    """
    client = _get_client_or_404(slug)

    # Get all item availabilities
    items_qs = MenuItem.objects.filter(
        client=client, category__menu__is_active=True
    ).values_list("pk", "is_available")
    items = {str(pk): is_avail for pk, is_avail in items_qs}

    # Get all modifier availabilities
    modifiers_qs = Modifier.objects.filter(
        client=client, group__item__category__menu__is_active=True
    ).values_list("pk", "is_available")
    modifiers = {str(pk): is_avail for pk, is_avail in modifiers_qs}

    response = AvailabilityResponse(
        items=items,
        modifiers=modifiers,
        as_of=datetime.now(UTC),
    )
    return _json_response(response.model_dump(mode="json"))


def options_handler(_request: HttpRequest, _slug: str) -> JsonResponse:
    """
    OPTIONS handler for CORS preflight requests.
    """
    response = JsonResponse({})
    for key, value in _cors_headers().items():
        response[key] = value
    return response
