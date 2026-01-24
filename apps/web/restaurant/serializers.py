"""
Pydantic schemas for menu API responses.

These schemas define the public API contract for menu data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Nested Menu Structure
# =============================================================================


class ModifierSchema(BaseModel):
    """A modifier option within a group."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_adjustment: Decimal
    is_available: bool


class ModifierGroupSchema(BaseModel):
    """A group of modifiers for a menu item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    min_selections: int
    max_selections: int
    modifiers: list[ModifierSchema] = Field(default_factory=list)

    @property
    def is_required(self) -> bool:
        """Check if at least one selection is required."""
        return self.min_selections > 0


class MenuItemSchema(BaseModel):
    """A menu item with full details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    image_url: str
    is_available: bool
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    allergens: list[str]
    modifier_groups: list[ModifierGroupSchema] = Field(default_factory=list)


class MenuCategorySchema(BaseModel):
    """A category within a menu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    items: list[MenuItemSchema] = Field(default_factory=list)


class MenuSchema(BaseModel):
    """A complete menu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    available_start: str | None = None  # HH:MM format
    available_end: str | None = None  # HH:MM format
    categories: list[MenuCategorySchema] = Field(default_factory=list)


# =============================================================================
# API Response Schemas
# =============================================================================


class MenuListResponse(BaseModel):
    """Response for GET /api/clients/{slug}/menu."""

    menus: list[MenuSchema]
    source: Literal["pos", "static"]
    last_synced_at: datetime | None = None


class SingleMenuResponse(BaseModel):
    """Response for GET /api/clients/{slug}/menu/{menu_id}."""

    menu: MenuSchema
    source: Literal["pos", "static"]


class AvailabilityResponse(BaseModel):
    """Response for GET /api/clients/{slug}/availability."""

    items: dict[str, bool]  # item_id -> is_available
    modifiers: dict[str, bool]  # modifier_id -> is_available
    as_of: datetime


# =============================================================================
# Order Schemas
# =============================================================================


class CustomerSchema(BaseModel):
    """Customer information for an order."""

    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: str = Field(default="", max_length=20)


class OrderModifierSelectionSchema(BaseModel):
    """Selected modifiers for an order item."""

    group_id: int
    selections: list[int] = Field(default_factory=list)


class OrderItemCreateSchema(BaseModel):
    """A single item in an order creation request."""

    menu_item_id: int
    quantity: int = Field(..., ge=1, le=99)
    modifiers: list[OrderModifierSelectionSchema] = Field(default_factory=list)
    special_instructions: str = Field(default="", max_length=500)


class OrderCreateRequest(BaseModel):
    """Request body for POST /api/clients/{slug}/orders."""

    customer: CustomerSchema
    order_type: Literal["pickup", "delivery"]
    scheduled_time: datetime | None = None
    items: list[OrderItemCreateSchema] = Field(..., min_length=1)
    special_instructions: str = Field(default="", max_length=1000)
    tip: Decimal = Field(default=Decimal("0"), ge=0)
    delivery_address: str = Field(default="", max_length=500)


class OrderItemResponseSchema(BaseModel):
    """A line item in an order response."""

    id: int
    item_name: str
    quantity: int
    unit_price: Decimal
    modifiers: list[dict[str, Any]]  # Snapshot of selected modifiers
    special_instructions: str
    line_total: Decimal


class OrderCreateResponse(BaseModel):
    """Response for POST /api/clients/{slug}/orders."""

    order_id: int
    confirmation_code: str
    status: str
    subtotal: Decimal
    tax: Decimal
    delivery_fee: Decimal
    tip: Decimal
    total: Decimal
    stripe_client_secret: str | None = None
    created_at: datetime


class OrderDetailResponse(BaseModel):
    """Response for GET /api/clients/{slug}/orders/{order_id}."""

    order_id: int
    confirmation_code: str
    status: str
    customer: CustomerSchema
    items: list[OrderItemResponseSchema]
    order_type: str
    scheduled_time: datetime | None
    special_instructions: str
    delivery_address: str
    subtotal: Decimal
    tax: Decimal
    delivery_fee: Decimal
    tip: Decimal
    total: Decimal
    created_at: datetime
    confirmed_at: datetime | None
    estimated_ready_time: datetime | None


class OrderConfirmRequest(BaseModel):
    """Request body for POST /api/clients/{slug}/orders/{order_id}/confirm."""

    payment_intent_id: str


class OrderConfirmResponse(BaseModel):
    """Response for POST /api/clients/{slug}/orders/{order_id}/confirm."""

    order_id: int
    confirmation_code: str
    status: str
    estimated_ready_time: datetime | None


class OrderStatusResponse(BaseModel):
    """Response for GET /api/clients/{slug}/orders/{order_id}/status."""

    status: str
    updated_at: datetime
    estimated_ready_time: datetime | None


class ValidationErrorDetail(BaseModel):
    """A single validation error."""

    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""

    error: Literal["validation_error"]
    details: list[ValidationErrorDetail]
