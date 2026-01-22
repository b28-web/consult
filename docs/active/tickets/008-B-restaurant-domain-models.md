# 008-B: Restaurant Domain Models and Migrations

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 1 (Foundation)

## Summary

Create Django models for restaurant-specific data: restaurant profiles, menus, categories, items, modifiers, and orders. All models follow the existing multi-tenancy pattern with `ClientScopedModel`.

## Acceptance Criteria

- [ ] `RestaurantProfile` model linking Client to POS configuration
- [ ] `Menu` model with name, description, availability times
- [ ] `MenuCategory` model with FK to Menu
- [ ] `MenuItem` model with pricing, availability (86'd), dietary info
- [ ] `ModifierGroup` model with min/max selections
- [ ] `Modifier` model with price adjustments
- [ ] `Order` model with customer info, status, pricing, Stripe reference
- [ ] `OrderItem` model with quantity and modifier snapshot
- [ ] All models inherit from `ClientScopedModel`
- [ ] `external_id` fields on all POS-synced models for provider ID mapping
- [ ] Proper indexes on frequently queried fields
- [ ] Migrations generated and tested
- [ ] Admin registration for all models
- [ ] Factory classes for testing

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

*To be updated during implementation*
