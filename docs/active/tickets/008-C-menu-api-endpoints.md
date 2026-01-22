# 008-C: Menu API Endpoints

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 1 (Foundation)

## Summary

Create REST API endpoints for retrieving menu data. These endpoints are used by the Astro frontend at build time (full menu) and runtime (availability polling). Endpoints are public (no auth required) but scoped by client slug.

## Acceptance Criteria

- [ ] `GET /api/clients/{slug}/menu` - Returns full menu structure
- [ ] `GET /api/clients/{slug}/menu/{menu_id}` - Returns single menu with items
- [ ] `GET /api/clients/{slug}/availability` - Returns item availability map
- [ ] Responses include nested categories, items, and modifiers
- [ ] Proper serialization with DRF or Pydantic
- [ ] Static fallback: Returns `static_menu_json` if no POS and no Menu records
- [ ] Caching headers for CDN (menu: 5min, availability: 30s)
- [ ] CORS enabled for Astro sites
- [ ] OpenAPI schema generated
- [ ] Integration tests

## Implementation Notes

### Endpoints

```
GET /api/clients/{slug}/menu
Response: {
  "menus": [
    {
      "id": 1,
      "name": "Dinner",
      "description": "...",
      "available_start": "17:00",
      "available_end": "22:00",
      "categories": [
        {
          "id": 1,
          "name": "Appetizers",
          "items": [
            {
              "id": 1,
              "name": "Bruschetta",
              "description": "...",
              "price": "12.00",
              "image_url": "...",
              "is_available": true,
              "is_vegetarian": true,
              "allergens": ["gluten"],
              "modifier_groups": [...]
            }
          ]
        }
      ]
    }
  ],
  "source": "pos" | "static",
  "last_synced_at": "2026-01-21T12:00:00Z"
}

GET /api/clients/{slug}/availability
Response: {
  "items": {
    "1": true,
    "2": false,  // 86'd
    "3": true
  },
  "modifiers": {
    "10": true,
    "11": false
  },
  "as_of": "2026-01-21T12:00:00Z"
}
```

### Caching Strategy

```python
from django.views.decorators.cache import cache_control

@cache_control(max_age=300, public=True)  # 5 minutes
def menu_list(request, slug): ...

@cache_control(max_age=30, public=True)   # 30 seconds
def availability(request, slug): ...
```

### Static Fallback Logic

```python
def get_menu_response(client_slug: str) -> MenuResponse:
    profile = RestaurantProfile.objects.filter(
        client__slug=client_slug
    ).first()

    menus = Menu.objects.filter(client__slug=client_slug, is_active=True)

    if menus.exists():
        return MenuResponse(menus=serialize_menus(menus), source="pos")

    if profile and profile.static_menu_json:
        return MenuResponse(menus=profile.static_menu_json, source="static")

    raise Http404("No menu configured")
```

### Directory Structure

```
apps/web/restaurant/
├── serializers.py    # DRF serializers for nested menu structure
├── views.py          # API views
└── urls.py           # URL routing
```

Add to `apps/web/config/urls.py`:
```python
path("api/clients/<slug:slug>/", include("restaurant.urls")),
```

## Dependencies

- 008-B (Restaurant models must exist)

## Progress

*To be updated during implementation*
