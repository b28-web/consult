"""
Menu and Order API views - Public endpoints for restaurant data.

These endpoints are used by Astro frontends:
- At build time: Full menu fetch for SSG
- At runtime: Availability polling for 86'd items
- At checkout: Order creation and status tracking
"""

import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from pydantic import ValidationError as PydanticValidationError

from apps.web.core.decorators import idempotency_key_required
from apps.web.core.models import Client
from apps.web.payments.services import (
    PaymentError,
    create_payment_intent,
    verify_payment_intent,
)
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
from apps.web.restaurant.serializers import (
    AvailabilityResponse,
    CustomerSchema,
    MenuCategorySchema,
    MenuItemSchema,
    MenuListResponse,
    MenuSchema,
    ModifierGroupSchema,
    ModifierSchema,
    OrderConfirmRequest,
    OrderConfirmResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderDetailResponse,
    OrderItemResponseSchema,
    OrderStatusResponse,
    SingleMenuResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


def _cors_headers() -> dict[str, str]:
    """CORS headers for Astro site access."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Idempotency-Key",
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


@csrf_exempt
@require_POST
@login_required
def sync_availability(request: HttpRequest, slug: str) -> JsonResponse:
    """
    POST /api/clients/{slug}/sync-availability

    Manually trigger availability sync from POS.
    Requires authenticated staff user with access to this client.

    This is a fallback for when webhooks are delayed or failing.
    """
    client = _get_client_or_404(slug)

    # Check user has access to this client
    user = request.user
    if not user.is_staff and getattr(user, "client", None) != client:
        raise PermissionDenied("You don't have permission to sync this client")

    # Get restaurant profile
    profile = _get_restaurant_profile(client)
    if not profile:
        return _json_response(
            {"error": "No restaurant profile configured"},
            status=400,
        )

    if not profile.pos_provider:
        return _json_response(
            {"error": "No POS provider configured"},
            status=400,
        )

    # Process any pending webhooks for this client
    # Late imports to avoid circular dependency
    from apps.web.pos.models import POSWebhookEvent, WebhookStatus  # noqa: PLC0415
    from apps.web.pos.services import process_webhook  # noqa: PLC0415

    pending_webhooks = POSWebhookEvent.objects.filter(
        client=client,
        status=WebhookStatus.PENDING,
    ).order_by("received_at")

    processed_count = 0
    errors = []

    for webhook in pending_webhooks[:50]:  # Limit to 50 per sync
        try:
            process_webhook(str(webhook.id))
            processed_count += 1
        except Exception as e:
            errors.append(str(e))

    return _json_response(
        {
            "status": "sync_complete",
            "webhooks_processed": processed_count,
            "errors": errors[:5] if errors else [],  # Limit error messages
        }
    )


# =============================================================================
# Order API Endpoints
# =============================================================================


def _generate_confirmation_code() -> str:
    """Generate a unique customer-facing confirmation code."""
    # Format: ORD-XXXX where X is alphanumeric
    return f"ORD-{secrets.token_hex(2).upper()}"


def _validate_order_items(
    client: Client, items: list[dict[str, Any]]
) -> tuple[list[ValidationErrorDetail], list[tuple[MenuItem, dict[str, Any]]]]:
    """
    Validate all order items exist, are available, and modifiers are valid.

    Returns:
        Tuple of (errors, validated_items)
        where validated_items is a list of (MenuItem, item_data) tuples
    """
    errors: list[ValidationErrorDetail] = []
    validated_items: list[tuple[MenuItem, dict[str, Any]]] = []

    for i, item_data in enumerate(items):
        field_prefix = f"items[{i}]"

        # Check item exists
        try:
            menu_item = MenuItem.objects.select_related("category__menu").get(
                client=client,
                pk=item_data["menu_item_id"],
            )
        except MenuItem.DoesNotExist:
            errors.append(
                ValidationErrorDetail(
                    field=f"{field_prefix}.menu_item_id",
                    message="Item not found",
                )
            )
            continue

        # Check item is from an active menu
        if not menu_item.category.menu.is_active:
            errors.append(
                ValidationErrorDetail(
                    field=f"{field_prefix}.menu_item_id",
                    message=f"'{menu_item.name}' is not currently on the menu",
                )
            )
            continue

        # Check item is available (not 86'd)
        if not menu_item.is_available:
            errors.append(
                ValidationErrorDetail(
                    field=f"{field_prefix}.menu_item_id",
                    message=f"'{menu_item.name}' is currently unavailable",
                )
            )
            continue

        # Validate modifiers
        modifier_errors = _validate_modifiers(menu_item, item_data.get("modifiers", []))
        for error in modifier_errors:
            errors.append(
                ValidationErrorDetail(
                    field=f"{field_prefix}.modifiers",
                    message=error,
                )
            )

        validated_items.append((menu_item, item_data))

    return errors, validated_items


def _validate_modifiers(
    menu_item: MenuItem, modifier_selections: list[dict[str, Any]]
) -> list[str]:
    """
    Validate modifier selections for a menu item.

    Returns list of error messages.
    """
    errors: list[str] = []

    # Get all modifier groups for this item
    modifier_groups = {
        mg.pk: mg
        for mg in menu_item.modifier_groups.prefetch_related("modifiers").all()
    }

    # Track which groups have been selected
    selected_groups: dict[int, list[int]] = {}

    for selection in modifier_selections:
        group_id = selection.get("group_id")
        selections = selection.get("selections", [])

        if group_id not in modifier_groups:
            errors.append(f"Modifier group {group_id} not found for '{menu_item.name}'")
            continue

        group = modifier_groups[group_id]
        selected_groups[group_id] = selections

        # Validate selection count
        if len(selections) < group.min_selections:
            errors.append(
                f"'{group.name}' requires at least {group.min_selections} selection(s)"
            )
        if len(selections) > group.max_selections:
            errors.append(
                f"'{group.name}' allows at most {group.max_selections} selection(s)"
            )

        # Validate modifier IDs exist and are available
        valid_modifier_ids = {m.pk for m in group.modifiers.all()}
        for mod_id in selections:
            if mod_id not in valid_modifier_ids:
                errors.append(f"Modifier {mod_id} not found in '{group.name}'")
            else:
                # Check availability
                modifier = group.modifiers.get(pk=mod_id)
                if not modifier.is_available:
                    errors.append(f"'{modifier.name}' is currently unavailable")

    # Check required groups have selections
    for group_id, group in modifier_groups.items():
        if group.min_selections > 0 and group_id not in selected_groups:
            errors.append(f"'{group.name}' is required")

    return errors


def _calculate_item_price(
    menu_item: MenuItem, modifier_selections: list[dict[str, Any]]
) -> tuple[Decimal, list[dict[str, Any]]]:
    """
    Calculate the price for a single item including modifiers.

    Returns:
        Tuple of (unit_price, modifier_snapshot)
    """
    price = menu_item.price
    modifier_snapshot: list[dict[str, Any]] = []

    for selection in modifier_selections:
        group_id = selection.get("group_id")
        selections = selection.get("selections", [])

        if group_id is None:
            continue

        try:
            group = menu_item.modifier_groups.get(pk=int(group_id))
        except (ModifierGroup.DoesNotExist, ValueError, TypeError):
            continue

        for mod_id in selections:
            try:
                modifier = group.modifiers.get(pk=mod_id)
                price += modifier.price_adjustment
                modifier_snapshot.append(
                    {
                        "group_id": group_id,
                        "group_name": group.name,
                        "modifier_id": mod_id,
                        "modifier_name": modifier.name,
                        "price_adjustment": str(modifier.price_adjustment),
                    }
                )
            except Modifier.DoesNotExist:
                continue

    return price, modifier_snapshot


def _calculate_order_totals(
    items: list[tuple[MenuItem, dict[str, Any], Decimal, list[dict[str, Any]]]],
    tip: Decimal,
    order_type: str,
    profile: RestaurantProfile | None,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Calculate order totals.

    Args:
        items: List of (menu_item, item_data, unit_price, modifier_snapshot)
        tip: Tip amount
        order_type: 'pickup' or 'delivery'
        profile: Restaurant profile for tax rate and delivery fee

    Returns:
        Tuple of (subtotal, tax, delivery_fee, total)
    """
    # Calculate subtotal
    subtotal = Decimal("0")
    for _menu_item, item_data, unit_price, _modifier_snapshot in items:
        quantity = item_data.get("quantity", 1)
        subtotal += unit_price * quantity

    # Calculate tax
    tax_rate = profile.tax_rate if profile else Decimal("0.08")
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))

    # Calculate delivery fee
    delivery_fee = Decimal("0")
    if order_type == OrderType.DELIVERY and profile and profile.delivery_fee:
        delivery_fee = profile.delivery_fee

    # Calculate total
    total = subtotal + tax + delivery_fee + tip

    return subtotal, tax, delivery_fee, total


@csrf_exempt
@require_POST
@idempotency_key_required
def create_order(request: HttpRequest, slug: str) -> JsonResponse:  # noqa: PLR0911
    """
    POST /api/clients/{slug}/orders

    Create a new order and return Stripe client secret for payment.

    Request body: OrderCreateRequest schema
    Response: OrderCreateResponse schema (201) or ValidationErrorResponse (400)
    """
    client = _get_client_or_404(slug)
    profile = _get_restaurant_profile(client)

    # Check ordering is enabled
    if profile and not profile.ordering_enabled:
        return _json_response(
            {"error": "Online ordering is not enabled for this restaurant"},
            status=400,
        )

    # Parse and validate request body
    try:
        body = json.loads(request.body)
        order_request = OrderCreateRequest.model_validate(body)
    except json.JSONDecodeError:
        return _json_response(
            {"error": "Invalid JSON in request body"},
            status=400,
        )
    except PydanticValidationError as e:
        errors = [
            ValidationErrorDetail(
                field=".".join(str(loc) for loc in err["loc"]),
                message=err["msg"],
            )
            for err in e.errors()
        ]
        response = ValidationErrorResponse(error="validation_error", details=errors)
        return _json_response(response.model_dump(), status=400)

    # Validate order type
    if order_request.order_type == "delivery":
        if profile and not profile.delivery_enabled:
            return _json_response(
                {"error": "Delivery is not available for this restaurant"},
                status=400,
            )
        if not order_request.delivery_address:
            response = ValidationErrorResponse(
                error="validation_error",
                details=[
                    ValidationErrorDetail(
                        field="delivery_address",
                        message="Delivery address is required for delivery orders",
                    )
                ],
            )
            return _json_response(response.model_dump(), status=400)

    # Validate all items
    items_data = [item.model_dump() for item in order_request.items]
    errors, validated_items = _validate_order_items(client, items_data)

    if errors:
        response = ValidationErrorResponse(error="validation_error", details=errors)
        return _json_response(response.model_dump(), status=400)

    # Calculate prices for each item
    priced_items: list[
        tuple[MenuItem, dict[str, Any], Decimal, list[dict[str, Any]]]
    ] = []
    for menu_item, item_data in validated_items:
        unit_price, modifier_snapshot = _calculate_item_price(
            menu_item, item_data.get("modifiers", [])
        )
        priced_items.append((menu_item, item_data, unit_price, modifier_snapshot))

    # Calculate totals
    subtotal, tax, delivery_fee, total = _calculate_order_totals(
        priced_items,
        order_request.tip,
        order_request.order_type,
        profile,
    )

    # Create order and items in a transaction
    try:
        with transaction.atomic():
            confirmation_code = _generate_confirmation_code()

            order = Order.objects.create(
                client=client,
                customer_name=order_request.customer.name,
                customer_email=order_request.customer.email,
                customer_phone=order_request.customer.phone,
                order_type=order_request.order_type,
                scheduled_time=order_request.scheduled_time,
                special_instructions=order_request.special_instructions,
                delivery_address=order_request.delivery_address,
                subtotal=subtotal,
                tax=tax,
                delivery_fee=delivery_fee,
                tip=order_request.tip,
                total=total,
                status=OrderStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                confirmation_code=confirmation_code,
            )

            # Create order items
            for menu_item, item_data, unit_price, modifier_snapshot in priced_items:
                quantity = item_data.get("quantity", 1)
                line_total = unit_price * quantity

                OrderItem.objects.create(
                    client=client,
                    order=order,
                    menu_item=menu_item,
                    item_name=menu_item.name,
                    quantity=quantity,
                    unit_price=unit_price,
                    modifiers=modifier_snapshot,
                    special_instructions=item_data.get("special_instructions", ""),
                    line_total=line_total,
                )

            # Create Stripe PaymentIntent
            payment_intent = create_payment_intent(
                amount=total,
                metadata={
                    "order_id": str(order.pk),
                    "client_slug": slug,
                    "confirmation_code": confirmation_code,
                },
            )

            # Save payment intent ID
            order.stripe_payment_intent_id = payment_intent.id
            order.save(update_fields=["stripe_payment_intent_id"])

    except PaymentError as e:
        return _json_response(
            {"error": "Payment processing failed", "details": e.message},
            status=500,
        )

    # Build response
    order_response = OrderCreateResponse(
        order_id=order.pk,
        confirmation_code=order.confirmation_code,
        status=order.status,
        subtotal=subtotal,
        tax=tax,
        delivery_fee=delivery_fee,
        tip=order_request.tip,
        total=total,
        stripe_client_secret=payment_intent.client_secret,
        created_at=order.created_at,
    )

    return _json_response(order_response.model_dump(mode="json"), status=201)


@require_GET
def get_order(_request: HttpRequest, slug: str, order_id: int) -> JsonResponse:
    """
    GET /api/clients/{slug}/orders/{order_id}

    Get order details by ID.

    Response: OrderDetailResponse schema (200) or 404
    """
    client = _get_client_or_404(slug)

    try:
        order = Order.objects.prefetch_related("items").get(
            client=client,
            pk=order_id,
        )
    except Order.DoesNotExist as exc:
        raise Http404(f"Order {order_id} not found") from exc

    # Build items response
    items = [
        OrderItemResponseSchema(
            id=item.pk,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            modifiers=item.modifiers,
            special_instructions=item.special_instructions,
            line_total=item.line_total,
        )
        for item in order.items.all()
    ]

    response = OrderDetailResponse(
        order_id=order.pk,
        confirmation_code=order.confirmation_code,
        status=order.status,
        customer=CustomerSchema(
            name=order.customer_name,
            email=order.customer_email,
            phone=order.customer_phone,
        ),
        items=items,
        order_type=order.order_type,
        scheduled_time=order.scheduled_time,
        special_instructions=order.special_instructions,
        delivery_address=order.delivery_address,
        subtotal=order.subtotal,
        tax=order.tax,
        delivery_fee=order.delivery_fee,
        tip=order.tip,
        total=order.total,
        created_at=order.created_at,
        confirmed_at=order.confirmed_at,
        estimated_ready_time=order.estimated_ready_time,
    )

    return _json_response(response.model_dump(mode="json"))


@csrf_exempt
@require_POST
def confirm_order(request: HttpRequest, slug: str, order_id: int) -> JsonResponse:
    """
    POST /api/clients/{slug}/orders/{order_id}/confirm

    Confirm order after successful payment and submit to POS.

    Request body: OrderConfirmRequest schema
    Response: OrderConfirmResponse schema (200) or error
    """
    client = _get_client_or_404(slug)

    try:
        order = Order.objects.get(
            client=client,
            pk=order_id,
        )
    except Order.DoesNotExist as exc:
        raise Http404(f"Order {order_id} not found") from exc

    # Check order is in correct state
    if order.status != OrderStatus.PENDING:
        return _json_response(
            {"error": f"Order is already {order.status}"},
            status=400,
        )

    # Parse request
    try:
        body = json.loads(request.body)
        confirm_request = OrderConfirmRequest.model_validate(body)
    except json.JSONDecodeError:
        return _json_response(
            {"error": "Invalid JSON in request body"},
            status=400,
        )
    except PydanticValidationError as e:
        return _json_response(
            {"error": "Invalid request", "details": e.errors()},
            status=400,
        )

    # Verify payment
    if not verify_payment_intent(confirm_request.payment_intent_id):
        return _json_response(
            {"error": "Payment verification failed"},
            status=400,
        )

    # Verify payment intent matches order
    if order.stripe_payment_intent_id != confirm_request.payment_intent_id:
        return _json_response(
            {"error": "Payment intent does not match order"},
            status=400,
        )

    # Update order status
    now = datetime.now(UTC)
    estimated_ready = now + timedelta(minutes=30)  # Default 30 min estimate

    order.status = OrderStatus.CONFIRMED
    order.payment_status = PaymentStatus.CAPTURED
    order.confirmed_at = now
    order.estimated_ready_time = estimated_ready
    order.save(
        update_fields=[
            "status",
            "payment_status",
            "confirmed_at",
            "estimated_ready_time",
        ]
    )

    # Submit order to POS system
    from apps.web.pos.tasks import submit_order_to_pos_task  # noqa: PLC0415

    pos_result = submit_order_to_pos_task(order.pk)

    # Reload order to get any updates from POS submission
    order.refresh_from_db()

    response = OrderConfirmResponse(
        order_id=order.pk,
        confirmation_code=order.confirmation_code,
        status=order.status,
        estimated_ready_time=order.estimated_ready_time,
    )

    # Add POS submission info to response if relevant
    response_data = response.model_dump(mode="json")
    if pos_result.get("external_id"):
        response_data["pos_order_id"] = pos_result["external_id"]
    if not pos_result.get("success") and pos_result.get("error"):
        response_data["pos_warning"] = pos_result["error"]

    return _json_response(response_data)


@require_GET
@cache_control(max_age=5, public=True)  # 5 seconds
def order_status(_request: HttpRequest, slug: str, order_id: int) -> JsonResponse:
    """
    GET /api/clients/{slug}/orders/{order_id}/status

    Get current order status for polling.

    Response: OrderStatusResponse schema (200) or 404
    """
    client = _get_client_or_404(slug)

    try:
        order = Order.objects.get(
            client=client,
            pk=order_id,
        )
    except Order.DoesNotExist as exc:
        raise Http404(f"Order {order_id} not found") from exc

    response = OrderStatusResponse(
        status=order.status,
        updated_at=order.updated_at,
        estimated_ready_time=order.estimated_ready_time,
    )

    return _json_response(response.model_dump(mode="json"))


def order_options_handler(
    _request: HttpRequest, _slug: str, _order_id: int | None = None
) -> JsonResponse:
    """
    OPTIONS handler for CORS preflight requests on order endpoints.
    """
    response = JsonResponse({})
    for key, value in _cors_headers().items():
        response[key] = value
    return response


@csrf_exempt
@require_POST
@login_required
def retry_pos_submission(
    request: HttpRequest, slug: str, order_id: int
) -> JsonResponse:
    """
    POST /api/clients/{slug}/orders/{order_id}/retry-pos

    Manually retry POS submission for a failed order.
    Requires authenticated staff user with access to this client.

    Response: Dict with retry result
    """
    client = _get_client_or_404(slug)

    # Check user has access to this client
    user = request.user
    if not user.is_staff and getattr(user, "client", None) != client:
        raise PermissionDenied("You don't have permission to retry this order")

    try:
        order = Order.objects.get(
            client=client,
            pk=order_id,
        )
    except Order.DoesNotExist as exc:
        raise Http404(f"Order {order_id} not found") from exc

    # Only allow retry for failed orders
    if order.status != "pos_failed":
        return _json_response(
            {
                "error": f"Order is not in failed state (current: {order.status})",
                "hint": "Only orders with status 'pos_failed' can be retried",
            },
            status=400,
        )

    # Retry POS submission
    from apps.web.pos.tasks import retry_failed_order  # noqa: PLC0415

    result = retry_failed_order(order_id)

    if result.get("success"):
        # Reload order to get updates
        order.refresh_from_db()
        return _json_response(
            {
                "status": "success",
                "order_id": order.pk,
                "order_status": order.status,
                "external_id": result.get("external_id"),
                "confirmation_code": order.confirmation_code,
            }
        )
    else:
        return _json_response(
            {
                "status": "failed",
                "order_id": order_id,
                "error": result.get("error"),
                "is_retryable": result.get("is_retryable", False),
            },
            status=500,
        )
