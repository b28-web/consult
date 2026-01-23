"""
Pydantic schemas for menu API responses.

These schemas define the public API contract for menu data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

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
