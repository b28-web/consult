# 008-M: First Restaurant Client Deployment

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** pending
**Phase:** 5 (Production Deployment)

## Summary

Deploy the first live restaurant client using the new restaurant client type infrastructure. This validates the entire stack end-to-end: menu display, real-time availability, online ordering, payments, and POS integration.

## Acceptance Criteria

- [ ] Restaurant client selected and onboarded
- [ ] Client record created in Django with RestaurantProfile
- [ ] POS integration configured (Toast, Clover, or Square)
- [ ] POS credentials stored in Doppler
- [ ] Menu synced from POS to database
- [ ] Restaurant site scaffolded from template
- [ ] Site customized with branding (logo, colors, copy)
- [ ] Menu page displaying correctly with 86'd items
- [ ] Online ordering flow working end-to-end
- [ ] Test orders placed successfully
- [ ] Production Stripe keys configured
- [ ] Site deployed to Cloudflare Pages
- [ ] Custom domain configured
- [ ] SSL certificate active
- [ ] Monitoring/alerting set up
- [ ] Restaurant staff trained on dashboard
- [ ] Go-live checklist completed

## Implementation Notes

### Client Onboarding Checklist

**Pre-deployment:**
- [ ] Contract signed
- [ ] POS provider identified
- [ ] POS API credentials obtained
- [ ] Menu content reviewed for accuracy
- [ ] Branding assets collected (logo, colors)
- [ ] Business hours confirmed
- [ ] Pickup/delivery options confirmed
- [ ] Tax rate confirmed

**Technical setup:**
```bash
# 1. Create client in Django admin or via script
doppler run -- uv run python apps/web/manage.py shell
>>> from apps.web.core.models import Client
>>> from apps.web.restaurant.models import RestaurantProfile
>>> client = Client.objects.create(
...     slug="tonys-pizza",
...     name="Tony's Pizza",
...     email="tony@tonyspizza.com",
...     phone="+15555551234",
... )
>>> RestaurantProfile.objects.create(
...     client=client,
...     pos_provider="toast",
...     pos_location_id="abc123",
...     ordering_enabled=True,
... )

# 2. Add POS credentials to Doppler
doppler secrets set TONYS_PIZZA_TOAST_CLIENT_ID="xxx"
doppler secrets set TONYS_PIZZA_TOAST_CLIENT_SECRET="xxx"

# 3. Scaffold site from template
cp -r sites/_template-restaurant sites/tonys-pizza

# 4. Customize site config
# Edit sites/tonys-pizza/src/config.ts

# 5. Initial menu sync
doppler run -- uv run python apps/web/manage.py sync_menu tonys-pizza

# 6. Deploy site
cd sites/tonys-pizza
doppler run -- wrangler pages deploy
```

### Site Customization

**Config updates (src/config.ts):**
```typescript
export const config: RestaurantConfig = {
  client: {
    slug: "tonys-pizza",
    name: "Tony's Pizza",
    tagline: "Authentic New York Style Since 1985",
    phone: "+1 (555) 555-1234",
    email: "orders@tonyspizza.com",
    address: "123 Main St, Anytown, USA 12345",
  },
  restaurant: {
    cuisine: ["Italian", "Pizza"],
    priceRange: "$$",
    hours: {
      monday: [{ open: "11:00", close: "22:00" }],
      tuesday: [{ open: "11:00", close: "22:00" }],
      wednesday: [{ open: "11:00", close: "22:00" }],
      thursday: [{ open: "11:00", close: "22:00" }],
      friday: [{ open: "11:00", close: "23:00" }],
      saturday: [{ open: "11:00", close: "23:00" }],
      sunday: [{ open: "12:00", close: "21:00" }],
    },
    features: {
      dineIn: true,
      takeout: true,
      delivery: false,
      reservations: false,
      onlineOrdering: true,
    },
    pos: {
      provider: "toast",
      locationId: "abc123",
    },
  },
  intake: {
    formUrl: "https://intake.consult.io/tonys-pizza/form",
  },
  social: {
    instagram: "https://instagram.com/tonyspizza",
    facebook: "https://facebook.com/tonyspizza",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "Order Online", href: "/menu#order" },
    { label: "Contact", href: "/contact" },
  ],
};
```

**Branding updates:**
- Replace `public/logo.svg` with client logo
- Update `tailwind.config.ts` with brand colors
- Add hero image to `public/hero.jpg`
- Add menu item photos to `public/menu/`

### Testing Checklist

**Menu display:**
- [ ] All menu categories visible
- [ ] Items show correct prices
- [ ] Modifiers display and calculate correctly
- [ ] 86'd items show as unavailable
- [ ] Dietary badges (V, VG, GF) display correctly
- [ ] Allergen info accessible

**Availability polling:**
- [ ] 86 an item in POS
- [ ] Verify webhook received within 60 seconds
- [ ] Verify site shows item as unavailable
- [ ] Un-86 item, verify restoration

**Online ordering:**
- [ ] Add items to cart
- [ ] Modify quantities
- [ ] Add modifiers
- [ ] Remove items
- [ ] Cart persists across navigation
- [ ] Checkout form validates correctly
- [ ] Test payment with Stripe test card
- [ ] Order confirmation page displays
- [ ] Confirmation email received
- [ ] Order appears in POS system

**POS integration:**
- [ ] Order appears in POS kitchen display
- [ ] Order status updates flow back
- [ ] Test with various menu items and modifiers

### Domain Configuration

```bash
# Add custom domain to Cloudflare Pages
wrangler pages projects add-custom-domain tonys-pizza tonyspizza.com
wrangler pages projects add-custom-domain tonys-pizza www.tonyspizza.com

# Or configure via Cloudflare dashboard:
# Pages > tonys-pizza > Custom domains > Add
```

### Monitoring Setup

**Alerts to configure:**
- Webhook processing failures
- POS order submission failures
- Payment failures
- Site availability (Cloudflare)
- Error rate spikes

**Dashboards:**
- Daily order volume
- Average order value
- Popular items
- 86'd item frequency

### Staff Training

Topics to cover with restaurant staff:
1. Dashboard login and navigation
2. Viewing incoming orders
3. Order status updates
4. Handling 86'd items
5. Reviewing customer inquiries (inbox)
6. Contacting support

### Go-Live Checklist

```markdown
## Go-Live Checklist: [Client Name]

### Pre-Launch
- [ ] All tests passing
- [ ] Production Stripe keys configured
- [ ] POS credentials verified in production
- [ ] Menu data accurate and complete
- [ ] Site content reviewed and approved
- [ ] Custom domain configured
- [ ] SSL certificate active
- [ ] Monitoring alerts configured

### Launch Day
- [ ] DNS propagation complete
- [ ] Place test order with real payment
- [ ] Verify order in POS
- [ ] Verify confirmation email
- [ ] Staff notified of go-live
- [ ] Social media announcement (if planned)

### Post-Launch (Day 1)
- [ ] Monitor error logs
- [ ] Check webhook delivery
- [ ] Verify first real customer orders
- [ ] Address any staff questions
- [ ] Collect initial feedback

### Post-Launch (Week 1)
- [ ] Review order volume
- [ ] Check for recurring issues
- [ ] Gather customer feedback
- [ ] Optimize based on learnings
```

## Dependencies

- EP-006 (Dagger pipeline for deployment validation)
- EP-007 (Pulumi infrastructure for backend)
- All 008-A through 008-L tickets complete
- Toast/Clover/Square partnership (for order creation)

## Progress

*To be updated during implementation*
