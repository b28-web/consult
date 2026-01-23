# 008-D: Restaurant Site Template (Menu Display)

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 1 (Foundation)

## Summary

Create an Astro site template for restaurant clients with menu display, hours, location info, and the foundation for online ordering. The template fetches menu data at build time and polls for availability at runtime.

## Acceptance Criteria

- [x] `sites/_template-restaurant/` directory created
- [x] `RestaurantConfig` type extending `SiteConfig` in `src/config.ts`
- [x] Homepage with hero, hours, location, cuisine type
- [x] Menu page with categories, items, prices, descriptions
- [x] Menu items show dietary badges (V, VG, GF)
- [x] Menu items show allergen info on hover/click
- [x] 86'd items visually distinguished (grayed out, "Currently unavailable")
- [x] Availability polling every 60 seconds on menu page
- [x] Contact page with form (reuse existing intake pattern)
- [x] Responsive design (mobile-first for restaurant sites)
- [x] Image optimization for menu item photos (lazy loading)
- [x] SEO meta tags for restaurant (schema.org/Restaurant)
- [x] Build-time fetch from menu API
- [x] Works with static fallback (no API) for development

## Implementation Notes

### Directory Structure

```
sites/_template-restaurant/
├── src/
│   ├── config.ts                    # RestaurantConfig type + example
│   ├── env.d.ts
│   ├── layouts/
│   │   └── RestaurantLayout.astro   # Extends shared BaseLayout
│   ├── pages/
│   │   ├── index.astro              # Homepage
│   │   ├── menu.astro               # Full menu display
│   │   └── contact.astro            # Contact form
│   ├── components/
│   │   ├── Hours.astro              # Business hours display
│   │   ├── LocationMap.astro        # Address + embedded map
│   │   ├── MenuNav.astro            # Jump links to menu sections
│   │   ├── MenuSection.astro        # Category with items
│   │   ├── MenuItem.astro           # Individual item card
│   │   ├── DietaryBadges.astro      # V/VG/GF icons
│   │   ├── AllergenInfo.astro       # Allergen popup/tooltip
│   │   └── AvailabilityBadge.astro  # 86'd indicator
│   ├── lib/
│   │   ├── menu.ts                  # fetchMenu(), types
│   │   └── availability.ts          # Polling logic
│   └── styles/
│       └── restaurant.css           # Restaurant-specific styles
├── public/
│   └── placeholder-food.jpg         # Default menu item image
├── astro.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── wrangler.toml
└── package.json
```

### RestaurantConfig Type

```typescript
// src/config.ts
import type { SiteConfig } from "@consult/shared-ui";

export interface RestaurantConfig extends SiteConfig {
  restaurant: {
    cuisine: string[];
    priceRange: "$" | "$$" | "$$$" | "$$$$";
    hours: Record<string, { open: string; close: string }[] | "closed">;
    features: {
      dineIn: boolean;
      takeout: boolean;
      delivery: boolean;
      reservations: boolean;
      onlineOrdering: boolean;
    };
    pos?: {
      provider: "toast" | "clover" | "square" | null;
      locationId: string;
    };
  };
}

export const config: RestaurantConfig = {
  client: {
    slug: "template-restaurant",
    name: "Sample Restaurant",
    // ...
  },
  restaurant: {
    cuisine: ["American", "Burgers"],
    priceRange: "$$",
    hours: {
      monday: [{ open: "11:00", close: "21:00" }],
      tuesday: [{ open: "11:00", close: "21:00" }],
      // ...
      sunday: "closed",
    },
    features: {
      dineIn: true,
      takeout: true,
      delivery: false,
      reservations: false,
      onlineOrdering: false,  // Enabled in Phase 4
    },
  },
  // ...
};
```

### Menu Fetching

```typescript
// src/lib/menu.ts
export async function fetchMenu(slug: string): Promise<MenuResponse> {
  const apiUrl = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/clients/${slug}/menu`);
  if (!res.ok) throw new Error("Failed to fetch menu");
  return res.json();
}

// Used in menu.astro at build time:
// const menu = await fetchMenu(config.client.slug);
```

### Availability Polling

```typescript
// src/lib/availability.ts
export function startAvailabilityPolling(
  slug: string,
  onUpdate: (availability: AvailabilityMap) => void,
  intervalMs = 60000
) {
  const poll = async () => {
    const res = await fetch(`/api/clients/${slug}/availability`);
    if (res.ok) onUpdate(await res.json());
  };
  poll(); // Initial fetch
  return setInterval(poll, intervalMs);
}

// Client-side script in menu.astro updates DOM based on availability
```

### 86'd Item Display

```astro
<!-- MenuItem.astro -->
<div class={`menu-item ${!item.is_available ? 'opacity-50' : ''}`}>
  <div class="flex justify-between">
    <h3 class="font-semibold">{item.name}</h3>
    <span class="text-lg">${item.price}</span>
  </div>
  <p class="text-gray-600 text-sm">{item.description}</p>
  {!item.is_available && (
    <span class="text-red-500 text-sm">Currently unavailable</span>
  )}
  <DietaryBadges item={item} />
</div>
```

### Development Mode

For local development without API:
```typescript
// src/lib/menu.ts
export async function fetchMenu(slug: string): Promise<MenuResponse> {
  if (import.meta.env.DEV && !import.meta.env.PUBLIC_API_URL) {
    // Return mock data for development
    return import("../data/mock-menu.json");
  }
  // ... actual fetch
}
```

## Dependencies

- 008-C (Menu API endpoints for fetching data)
- Shared UI package (`packages/shared-ui`)

## Progress

### 2026-01-23
- **Complete**: All acceptance criteria met
- Created full `sites/_template-restaurant/` directory structure
- Configuration files: package.json, astro.config.mjs, tailwind.config.ts, tsconfig.json, wrangler.toml
- `RestaurantConfig` type with hours, cuisine, features, POS config
- **Layouts**: BaseLayout (with schema.org), PageLayout (nav, footer, hours)
- **Components**:
  - Hours.astro - Business hours with today highlighted
  - DietaryBadges.astro - V/VG/GF indicators
  - AllergenInfo.astro - Allergen warnings
  - MenuItem.astro - Full item card with modifiers
  - MenuSection.astro - Category with items
  - MenuNav.astro - Jump links to sections
- **Pages**:
  - index.astro - Hero, features, hours, location, CTA
  - menu.astro - Full menu with availability polling
  - contact.astro - Contact form + info
- **Lib**:
  - menu.ts - Types + fetchMenu() with mock fallback
  - availability.ts - Polling logic for 86'd items
- Mock menu data in src/data/mock-menu.json
- Build verified: 3 pages built successfully
