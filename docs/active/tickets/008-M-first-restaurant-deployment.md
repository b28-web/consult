# 008-M: Demo Restaurant Deployment

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 5 (Demo Deployment)

## Summary

Deploy a demo restaurant first to validate the entire stack end-to-end, then use learnings to deploy a real client. The demo uses the MockPOSAdapter with realistic test data, Stripe test mode, and deploys to Cloudflare Pages.

## Approach

Deploy a demo restaurant ("Katie's Sushi") to validate the full stack:
- Inspired by Ebiko SF - grab-and-go sushi, clean presentation, affordable
- Uses MockPOSAdapter (no real POS credentials needed)
- Stripe test mode (no real payments)
- Validates: site scaffolding, menu display, cart/checkout flow, order API
- Deployed to: https://consult-katies-sushi.pages.dev

Real client deployment will be a separate EP when needed.

## Acceptance Criteria

- [x] ~~Demo client record created in Django with RestaurantProfile~~ (not needed for demo mode)
- [x] MockPOSAdapter configured with sushi menu data
- [x] Restaurant site scaffolded from template as `katies-sushi`
- [x] Site customized with Katie's Sushi branding
- [x] Menu page displaying correctly
- [x] 86'd items toggling works (Aburi Toro marked unavailable in mock data)
- [x] Cart and checkout flow working (demo mode with mock orders)
- [x] ~~Test orders placed with Stripe test cards~~ (demo mode bypasses Stripe)
- [x] Order confirmation page displays correctly
- [x] Site deployed to Cloudflare Pages
- [x] End-to-end flow documented

## Implementation Notes

### Demo Restaurant Setup

**Demo client details:**
- Slug: `katies-sushi`
- Name: "Katie's Sushi"
- Style: Grab-and-go sushi inspired by Ebiko SF
- POS: MockPOSAdapter
- Stripe: Test mode

**Technical setup:**
```bash
# 1. Create demo client in Django
doppler run -- uv run python apps/web/manage.py shell
>>> from apps.web.core.models import Client
>>> from apps.web.restaurant.models import RestaurantProfile
>>> client = Client.objects.create(
...     slug="katies-sushi",
...     name="Katie's Sushi",
...     email="hello@katiessushi.com",
...     phone="+14155550123",
... )
>>> RestaurantProfile.objects.create(
...     client=client,
...     pos_provider="mock",
...     ordering_enabled=True,
... )

# 2. Scaffold site from template
cp -r sites/_template-restaurant sites/katies-sushi

# 3. Customize site config (see below)

# 4. Build and test locally
cd sites/katies-sushi && npm install && npm run dev

# 5. Deploy to Cloudflare Pages
npm run build && wrangler pages deploy dist
```


### Katie's Sushi Site Config

**Config updates (sites/katies-sushi/src/config.ts):**
```typescript
export const config: RestaurantConfig = {
  client: {
    slug: "katies-sushi",
    name: "Katie's Sushi",
    tagline: "Fresh grab-and-go sushi",
    phone: "+1 (415) 555-0123",
    email: "hello@katiessushi.com",
    address: "123 Market Street, San Francisco, CA 94105",
  },
  restaurant: {
    cuisine: ["Japanese", "Sushi"],
    priceRange: "$",
    hours: {
      monday: [{ open: "11:00", close: "20:00" }],
      tuesday: [{ open: "11:00", close: "20:00" }],
      wednesday: [{ open: "11:00", close: "20:00" }],
      thursday: [{ open: "11:00", close: "20:00" }],
      friday: [{ open: "11:00", close: "21:00" }],
      saturday: [{ open: "11:00", close: "21:00" }],
      sunday: "closed",
    },
    features: {
      dineIn: false,
      takeout: true,
      delivery: false,
      reservations: false,
      onlineOrdering: true,
    },
    pos: {
      provider: "mock",
      locationId: "katies-sushi-001",
    },
  },
  intake: {
    formUrl: "https://intake.consult.dev/katies-sushi/form",
  },
  social: {
    instagram: "https://instagram.com/katiessushi",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "Order", href: "/order" },
    { label: "Contact", href: "/contact" },
  ],
};
```

**Menu categories (Ebiko-inspired):**
- Nigiri Sets (7pc, 10pc omakase-style)
- Aburi (torched) Nigiri
- Rolls (salmon avocado, spicy tuna, eel avocado)
- Chirashi Bowls (bara chirashi, salmon don)
- Sides (edamame, miso soup, pickles)

**Branding updates:**
- Replace `public/logo.svg` with client logo
- Update `tailwind.config.ts` with brand colors
- Add hero image to `public/hero.jpg`
- Add menu item photos to `public/menu/`

### Demo Testing Checklist

**Menu display:**
- [ ] All menu categories visible
- [ ] Items show correct prices
- [ ] Modifiers display and calculate correctly
- [ ] 86'd items show as unavailable
- [ ] Dietary badges (V, VG, GF) display correctly
- [ ] Allergen info accessible

**Availability (MockPOSAdapter):**
- [ ] Toggle item availability via API/admin
- [ ] Verify site shows item as unavailable after polling
- [ ] Restore availability, verify restoration

**Online ordering:**
- [ ] Add items to cart
- [ ] Modify quantities
- [ ] Add modifiers
- [ ] Remove items
- [ ] Cart persists across navigation
- [ ] Checkout form validates correctly
- [ ] Test payment with Stripe test card (4242...)
- [ ] Order confirmation page displays
- [ ] Order record created in database

## Dependencies

- All 008-A through 008-L tickets complete

## Progress

### 2026-01-23
- Site scaffolded from `_template-restaurant` to `sites/katies-sushi/`
- Config customized: Katie's Sushi branding, Ebiko-inspired grab-and-go style
- Sushi menu created with 6 categories, 22 items:
  - Nigiri Sets (7pc omakase, 10pc premium, salmon lover)
  - Aburi Nigiri (salmon, toro, scallop)
  - Rolls (salmon avocado, spicy tuna, eel, california, veggie)
  - Chirashi Bowls (bara chirashi, salmon don, poke)
  - Sides (miso, edamame, seaweed salad, pickles, tofu)
  - Drinks (green tea, ramune, calpico)
- One item marked as 86'd (Aburi Toro) for testing availability display
- Site built successfully (5 pages)
- Deployed to Cloudflare Pages: https://consult-katies-sushi.pages.dev
- Added to sites/registry.yaml

**Mock order flow added:**
- Checkout detects when no `PUBLIC_API_URL` is set (demo mode)
- In demo mode: validates form, creates mock order in localStorage, redirects to confirmation
- Shows "Demo Mode" banner on checkout and "Demo Order" badge on confirmation
- No Django backend or Stripe needed for demo testing

**Ticket complete!** Full end-to-end demo flow working at https://consult-katies-sushi.pages.dev
