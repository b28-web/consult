"""
Restaurant models - Menus, items, modifiers, and orders.

All models follow the multi-tenancy pattern with ClientScopedModel.
POS-synced models have external_id fields for provider ID mapping.
"""

from django.db import models

from apps.web.core.models import ClientScopedModel


class POSProvider(models.TextChoices):
    """Supported POS providers."""

    TOAST = "toast", "Toast"
    CLOVER = "clover", "Clover"
    SQUARE = "square", "Square"


class RestaurantProfile(ClientScopedModel):
    """
    Restaurant-specific configuration for a client.

    Links a Client to their POS integration and display settings.
    OneToOne with Client (enforced by unique constraint).
    """

    # POS Integration
    pos_provider = models.CharField(
        max_length=20,
        choices=POSProvider.choices,
        blank=True,
        help_text="Connected POS system (blank = no POS)",
    )
    pos_location_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Location ID in the POS system",
    )
    pos_connected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When POS was connected",
    )

    # Fallback for non-POS clients
    static_menu_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Manual menu JSON for clients without POS integration",
    )

    # Display settings
    show_prices = models.BooleanField(default=True)
    show_descriptions = models.BooleanField(default=True)
    show_images = models.BooleanField(default=True)

    # Ordering configuration
    ordering_enabled = models.BooleanField(
        default=False,
        help_text="Allow online ordering",
    )
    pickup_enabled = models.BooleanField(default=True)
    delivery_enabled = models.BooleanField(default=False)
    delivery_radius_miles = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    delivery_minimum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Tax configuration
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Tax rate as decimal (e.g., 0.0825 for 8.25%)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client"],
                name="unique_restaurant_profile_per_client",
            ),
        ]

    def __str__(self) -> str:
        return f"Restaurant profile for {self.client}"

    @property
    def has_pos(self) -> bool:
        """Check if POS is connected."""
        return bool(self.pos_provider and self.pos_location_id)


class Menu(ClientScopedModel):
    """
    A menu (e.g., Breakfast, Lunch, Dinner, Drinks).

    Menus can have time-based availability.
    """

    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID in the POS system",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    # Time-based availability (optional)
    available_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time (e.g., 06:00 for breakfast)",
    )
    available_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End time (e.g., 11:00 for breakfast)",
    )

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["client", "is_active"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self) -> str:
        return self.name


class MenuCategory(ClientScopedModel):
    """
    Category within a menu (e.g., Appetizers, Entrees, Desserts).
    """

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID in the POS system",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "menu categories"
        indexes = [
            models.Index(fields=["menu", "display_order"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.menu.name} > {self.name}"


class MenuItem(ClientScopedModel):
    """
    Individual menu item.

    Tracks availability (86'd status) and dietary information.
    """

    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name="items",
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID in the POS system",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)

    # Availability (86'd when False)
    is_available = models.BooleanField(
        default=True,
        help_text="False = 86'd (unavailable)",
    )
    availability_updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When availability was last updated",
    )

    # Dietary information
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    allergens = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allergens (e.g., ["nuts", "dairy", "shellfish"])',
    )

    # Display
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["client", "category"]),
            models.Index(fields=["client", "is_available"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self) -> str:
        return self.name


class ModifierGroup(ClientScopedModel):
    """
    Group of modifiers for a menu item (e.g., "Choose your protein", "Add toppings").

    min_selections/max_selections control required vs optional modifiers.
    """

    item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="modifier_groups",
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID in the POS system",
    )
    name = models.CharField(max_length=200)
    min_selections = models.PositiveIntegerField(
        default=0,
        help_text="Minimum required (0 = optional)",
    )
    max_selections = models.PositiveIntegerField(
        default=1,
        help_text="Maximum allowed (1 = single choice)",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["item", "display_order"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.item.name} > {self.name}"

    @property
    def is_required(self) -> bool:
        """Check if at least one selection is required."""
        return self.min_selections > 0


class Modifier(ClientScopedModel):
    """
    Individual modifier option within a group.

    Can have a price adjustment (positive or negative).
    """

    group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID in the POS system",
    )
    name = models.CharField(max_length=200)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price change when selected (can be negative)",
    )
    is_available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["group", "display_order"]),
            models.Index(fields=["external_id"]),
        ]

    def __str__(self) -> str:
        if self.price_adjustment:
            sign = "+" if self.price_adjustment > 0 else ""
            return f"{self.name} ({sign}${self.price_adjustment})"
        return self.name


class OrderStatus(models.TextChoices):
    """Order lifecycle status."""

    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PREPARING = "preparing", "Preparing"
    READY = "ready", "Ready"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class OrderType(models.TextChoices):
    """Order fulfillment type."""

    PICKUP = "pickup", "Pickup"
    DELIVERY = "delivery", "Delivery"


class PaymentStatus(models.TextChoices):
    """Payment processing status."""

    PENDING = "pending", "Pending"
    AUTHORIZED = "authorized", "Authorized"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Order(ClientScopedModel):
    """
    Customer order.

    Tracks order lifecycle, payment, and POS synchronization.
    """

    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Order ID in the POS system",
    )

    # Customer information
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)

    # Order details
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
    )
    scheduled_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Requested pickup/delivery time (null = ASAP)",
    )
    special_instructions = models.TextField(blank=True)

    # Delivery address (if delivery order)
    delivery_address = models.TextField(blank=True)

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    tip = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe PaymentIntent ID",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # Timestamps
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When order was submitted to POS",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Confirmation
    confirmation_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Customer-facing confirmation code",
    )
    estimated_ready_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Estimated time order will be ready",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["client", "created_at"]),
            models.Index(fields=["stripe_payment_intent_id"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["confirmation_code"]),
        ]

    def __str__(self) -> str:
        return f"Order {self.confirmation_code or self.pk} - {self.customer_name}"


class OrderItem(ClientScopedModel):
    """
    Line item in an order.

    Stores a snapshot of the item and modifiers at order time.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="Reference to the menu item (for analytics)",
    )

    # Snapshot of item at order time
    item_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Modifier snapshot (stored as JSON to preserve order-time state)
    modifiers = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected modifiers with names and price adjustments",
    )

    special_instructions = models.TextField(blank=True)

    # Calculated line total
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="unit_price * quantity + modifier adjustments",
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.item_name}"
