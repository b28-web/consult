# 008-B: Restaurant Domain Models and Migrations

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 1 (Foundation)

## Summary

Create Django models for restaurant-specific data: restaurant profiles, menus, categories, items, modifiers, and orders. All models follow the existing multi-tenancy pattern with `ClientScopedModel`.

## Acceptance Criteria

- [x] `RestaurantProfile` model linking Client to POS configuration
- [x] `Menu` model with name, description, availability times
- [x] `MenuCategory` model with FK to Menu
- [x] `MenuItem` model with pricing, availability (86'd), dietary info
- [x] `ModifierGroup` model with min/max selections
- [x] `Modifier` model with price adjustments
- [x] `Order` model with customer info, status, pricing, Stripe reference
- [x] `OrderItem` model with quantity and modifier snapshot
- [x] All models inherit from `ClientScopedModel`
- [x] `external_id` fields on all POS-synced models for provider ID mapping
- [x] Proper indexes on frequently queried fields
- [x] Migrations generated and tested
- [x] Admin registration for all models
- [x] Factory classes for testing

## Implementation Notes

### Model Relationships

```
Client (1) ─── (1) RestaurantProfile
         │
         └──── (*) Menu
                   │
                   └── (*) MenuCategory
                            │
                            └── (*) MenuItem
                                     │
                                     └── (*) ModifierGroup
                                              │
                                              └── (*) Modifier

Client (1) ─── (*) Order
                   │
                   └── (*) OrderItem ─── (1) MenuItem
```

### Key Fields

**RestaurantProfile:**
- `pos_provider`: CharField choices (toast, clover, square, null)
- `pos_location_id`: For POS API calls
- `static_menu_json`: JSONField for non-POS fallback
- `ordering_enabled`: BooleanField

**MenuItem:**
- `is_available`: BooleanField (False = 86'd)
- `availability_updated_at`: Auto-updated timestamp
- `allergens`: JSONField list

**Order:**
- `status`: pending → confirmed → preparing → ready → completed / cancelled
- `order_type`: pickup, delivery
- `stripe_payment_intent_id`: For payment tracking
- `payment_status`: pending, succeeded, failed, refunded

### Indexes

```python
class MenuItem(ClientScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=["client", "category"]),
            models.Index(fields=["client", "is_available"]),
            models.Index(fields=["external_id"]),
        ]

class Order(ClientScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["client", "created_at"]),
            models.Index(fields=["stripe_payment_intent_id"]),
        ]
```

### Directory Structure

```
apps/web/restaurant/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── migrations/
│   └── 0001_initial.py
└── factories.py      # For testing
```

## Dependencies

- 008-A (POS adapter for type references, but models can be created first)

## Progress

### 2026-01-23

**Completed implementation:**

1. **Created `apps/web/restaurant/` module:**
   - `__init__.py` - Module docstring
   - `apps.py` - Django app config
   - `models.py` - All domain models
   - `admin.py` - Admin registration with inlines
   - `migrations/0001_initial.py` - Initial migration

2. **Models implemented:**
   - `RestaurantProfile` - POS config, ordering settings, tax rate
   - `Menu` - Name, description, time-based availability
   - `MenuCategory` - FK to Menu, display order
   - `MenuItem` - Price, 86'd status, dietary info, allergens
   - `ModifierGroup` - Min/max selections, required flag
   - `Modifier` - Price adjustment, availability
   - `Order` - Customer info, status lifecycle, Stripe payment
   - `OrderItem` - Quantity, modifier snapshot, line total

3. **Indexes added:**
   - Menu: client+is_active, external_id
   - MenuCategory: menu+display_order, external_id
   - MenuItem: client+category, client+is_available, external_id
   - ModifierGroup: item+display_order, external_id
   - Modifier: group+display_order, external_id
   - Order: client+status, client+created_at, stripe_payment_intent_id, external_id, confirmation_code

4. **Admin registration:**
   - All models registered with appropriate list displays
   - Inline editing for categories, items, modifiers, order items
   - Fieldsets organized by section

5. **Factory classes:**
   - ClientFactory, RestaurantProfileFactory
   - MenuFactory, MenuCategoryFactory, MenuItemFactory
   - ModifierGroupFactory, ModifierFactory
   - OrderFactory, OrderItemFactory

6. **Tests:** 26 tests covering all models and relationships
