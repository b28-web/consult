"""POS integration schemas - data contracts for Point of Sale systems."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class POSProvider(str, Enum):
    """Supported POS providers."""

    TOAST = "toast"
    CLOVER = "clover"
    SQUARE = "square"
    MOCK = "mock"


class OrderType(str, Enum):
    """Order fulfillment type."""

    PICKUP = "pickup"
    DELIVERY = "delivery"
    DINE_IN = "dine_in"


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment processing status."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


# =============================================================================
# Authentication
# =============================================================================


class POSCredentials(BaseModel):
    """Credentials for authenticating with a POS provider."""

    provider: POSProvider
    client_id: str
    client_secret: str
    location_id: str
    extra: dict[str, str] = Field(default_factory=dict)


class POSSession(BaseModel):
    """Authenticated session with a POS provider."""

    provider: POSProvider
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime


# =============================================================================
# Menu Data
# =============================================================================


class POSModifier(BaseModel):
    """A menu item modifier option."""

    external_id: str = Field(description="ID in the POS system")
    name: str
    price_adjustment: Decimal = Field(default=Decimal("0.00"))
    is_available: bool = True


class POSModifierGroup(BaseModel):
    """A group of modifiers for a menu item."""

    external_id: str
    name: str
    min_selections: int = 0
    max_selections: int = 1
    modifiers: list[POSModifier] = Field(default_factory=list)


class POSMenuItem(BaseModel):
    """A menu item from the POS system."""

    external_id: str
    name: str
    description: str = ""
    price: Decimal
    image_url: str = ""
    is_available: bool = True
    modifier_groups: list[POSModifierGroup] = Field(default_factory=list)

    # Dietary info
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    allergens: list[str] = Field(default_factory=list)


class POSMenuCategory(BaseModel):
    """A category within a menu."""

    external_id: str
    name: str
    description: str = ""
    items: list[POSMenuItem] = Field(default_factory=list)


class POSMenu(BaseModel):
    """A complete menu from the POS system."""

    external_id: str
    name: str
    description: str = ""
    categories: list[POSMenuCategory] = Field(default_factory=list)
    available_start: str | None = None  # HH:MM format
    available_end: str | None = None  # HH:MM format


# =============================================================================
# Orders
# =============================================================================


class POSOrderItemModifier(BaseModel):
    """Selected modifier for an order item."""

    external_id: str
    name: str
    price_adjustment: Decimal


class POSOrderItem(BaseModel):
    """Line item in a POS order."""

    menu_item_external_id: str
    name: str
    quantity: int = 1
    unit_price: Decimal
    modifiers: list[POSOrderItemModifier] = Field(default_factory=list)
    special_instructions: str = ""


class POSOrder(BaseModel):
    """Order to submit to the POS system."""

    # Customer info
    customer_name: str
    customer_email: str
    customer_phone: str = ""

    # Order details
    order_type: OrderType
    scheduled_time: datetime | None = None
    special_instructions: str = ""

    # Items
    items: list[POSOrderItem]

    # Pricing (calculated before submission)
    subtotal: Decimal
    tax: Decimal
    tip: Decimal = Decimal("0.00")
    total: Decimal


class POSOrderResult(BaseModel):
    """Result of creating an order in the POS system."""

    external_id: str = Field(description="Order ID in the POS system")
    status: OrderStatus
    estimated_ready_time: datetime | None = None
    confirmation_code: str | None = None


class POSOrderStatus(BaseModel):
    """Current status of an order in the POS system."""

    external_id: str
    status: OrderStatus
    estimated_ready_time: datetime | None = None
    updated_at: datetime


# =============================================================================
# Webhooks
# =============================================================================


class POSWebhookEventBase(BaseModel):
    """Base for all POS webhook events."""

    provider: POSProvider
    event_id: str
    occurred_at: datetime


class MenuUpdatedEvent(POSWebhookEventBase):
    """Menu was updated in the POS system."""

    event_type: Literal["menu_updated"] = "menu_updated"
    menu_id: str


class ItemAvailabilityChangedEvent(POSWebhookEventBase):
    """Item availability (86'd status) changed."""

    event_type: Literal["item_availability_changed"] = "item_availability_changed"
    item_id: str
    is_available: bool


class OrderStatusChangedEvent(POSWebhookEventBase):
    """Order status changed in the POS system."""

    event_type: Literal["order_status_changed"] = "order_status_changed"
    order_id: str
    status: OrderStatus
    previous_status: OrderStatus | None = None


# Union type for all webhook events
POSWebhookEvent = (
    MenuUpdatedEvent | ItemAvailabilityChangedEvent | OrderStatusChangedEvent
)
