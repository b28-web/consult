"""Admin registration for restaurant models."""

from django.contrib import admin

from apps.web.restaurant.models import (
    Menu,
    MenuCategory,
    MenuItem,
    Modifier,
    ModifierGroup,
    Order,
    OrderItem,
    RestaurantProfile,
)


class MenuCategoryInline(admin.TabularInline):
    """Inline for categories within a menu."""

    model = MenuCategory
    extra = 0
    fields = ["name", "description", "display_order"]


class MenuItemInline(admin.TabularInline):
    """Inline for items within a category."""

    model = MenuItem
    extra = 0
    fields = ["name", "price", "is_available", "display_order"]


class ModifierGroupInline(admin.TabularInline):
    """Inline for modifier groups within an item."""

    model = ModifierGroup
    extra = 0
    fields = ["name", "min_selections", "max_selections", "display_order"]


class ModifierInline(admin.TabularInline):
    """Inline for modifiers within a group."""

    model = Modifier
    extra = 0
    fields = ["name", "price_adjustment", "is_available", "display_order"]


class OrderItemInline(admin.TabularInline):
    """Inline for items within an order."""

    model = OrderItem
    extra = 0
    fields = ["item_name", "quantity", "unit_price", "line_total"]
    readonly_fields = ["item_name", "quantity", "unit_price", "line_total"]


@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    """Admin for restaurant profiles."""

    list_display = ["client", "pos_provider", "ordering_enabled", "has_pos"]
    list_filter = ["pos_provider", "ordering_enabled"]
    search_fields = ["client__name", "client__slug"]
    readonly_fields = ["created_at", "updated_at", "pos_connected_at"]

    fieldsets = [
        (None, {"fields": ["client"]}),
        (
            "POS Integration",
            {"fields": ["pos_provider", "pos_location_id", "pos_connected_at"]},
        ),
        (
            "Display Settings",
            {"fields": ["show_prices", "show_descriptions", "show_images"]},
        ),
        (
            "Ordering",
            {
                "fields": [
                    "ordering_enabled",
                    "pickup_enabled",
                    "delivery_enabled",
                    "delivery_radius_miles",
                    "delivery_minimum",
                    "delivery_fee",
                ]
            },
        ),
        ("Tax", {"fields": ["tax_rate"]}),
        ("Fallback", {"fields": ["static_menu_json"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin for menus."""

    list_display = ["name", "client", "is_active", "available_start", "available_end"]
    list_filter = ["is_active", "client"]
    search_fields = ["name", "client__name"]
    inlines = [MenuCategoryInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    """Admin for menu categories."""

    list_display = ["name", "menu", "client", "display_order"]
    list_filter = ["menu__client", "menu"]
    search_fields = ["name", "menu__name"]
    inlines = [MenuItemInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin for menu items."""

    list_display = [
        "name",
        "category",
        "price",
        "is_available",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
    ]
    list_filter = [
        "is_available",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
        "category__menu__client",
    ]
    search_fields = ["name", "description"]
    inlines = [ModifierGroupInline]
    readonly_fields = ["created_at", "updated_at", "availability_updated_at"]

    fieldsets = [
        (None, {"fields": ["client", "category", "name", "description", "price"]}),
        ("Media", {"fields": ["image_url"]}),
        (
            "Availability",
            {"fields": ["is_available", "availability_updated_at", "display_order"]},
        ),
        (
            "Dietary Information",
            {"fields": ["is_vegetarian", "is_vegan", "is_gluten_free", "allergens"]},
        ),
        ("POS", {"fields": ["external_id"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    """Admin for modifier groups."""

    list_display = ["name", "item", "min_selections", "max_selections", "is_required"]
    list_filter = ["item__category__menu__client"]
    search_fields = ["name", "item__name"]
    inlines = [ModifierInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    """Admin for modifiers."""

    list_display = ["name", "group", "price_adjustment", "is_available"]
    list_filter = ["is_available", "group__item__category__menu__client"]
    search_fields = ["name", "group__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin for orders."""

    list_display = [
        "confirmation_code",
        "customer_name",
        "client",
        "status",
        "order_type",
        "total",
        "payment_status",
        "created_at",
    ]
    list_filter = ["status", "order_type", "payment_status", "client"]
    search_fields = [
        "confirmation_code",
        "customer_name",
        "customer_email",
        "customer_phone",
    ]
    inlines = [OrderItemInline]
    readonly_fields = [
        "created_at",
        "updated_at",
        "submitted_at",
        "confirmed_at",
        "ready_at",
        "completed_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = [
        (None, {"fields": ["client", "confirmation_code", "external_id"]}),
        (
            "Customer",
            {"fields": ["customer_name", "customer_email", "customer_phone"]},
        ),
        (
            "Order Details",
            {
                "fields": [
                    "status",
                    "order_type",
                    "scheduled_time",
                    "special_instructions",
                    "delivery_address",
                ]
            },
        ),
        (
            "Pricing",
            {"fields": ["subtotal", "tax", "delivery_fee", "tip", "total"]},
        ),
        (
            "Payment",
            {"fields": ["stripe_payment_intent_id", "payment_status"]},
        ),
        (
            "Timing",
            {"fields": ["estimated_ready_time"]},
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                    "submitted_at",
                    "confirmed_at",
                    "ready_at",
                    "completed_at",
                ]
            },
        ),
    ]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin for order items."""

    list_display = ["item_name", "order", "quantity", "unit_price", "line_total"]
    list_filter = ["order__client"]
    search_fields = ["item_name", "order__confirmation_code"]
    readonly_fields = ["created_at", "updated_at"]
