# 005-C: Deploy hauler Site (+ Cal.com)

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Deploy junk hauler site with Cal.com booking integration.

## Acceptance Criteria

- [x] Site created at `sites/hauler/`
- [x] Config: Quick Haul Co, bold blue/orange theme
- [x] Pages: Home, Services, Pricing, Book Now, Contact
- [x] Cal.com embed on Book Now page
- [x] Quote request form on Services page
- [x] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Quick Haul Co
- Tagline: "Same-day junk removal, no hassle"
- Colors: Bold blue (#1d4ed8), Orange accent (#ea580c)

Services:
- Residential Junk Removal
- Commercial Cleanouts
- Construction Debris
- Appliance Disposal
- Estate Cleanouts

Cal.com config:
```typescript
// src/config.ts
calcom: {
  username: "quickhaul",
  eventSlug: "pickup",
}
```

Book Now page:
```astro
---
import CalEmbed from '@/components/CalEmbed.astro';
import { config } from '@/config';
---
<section>
  <h1>Book Your Pickup</h1>
  <CalEmbed
    username={config.calcom.username}
    eventSlug={config.calcom.eventSlug}
    mode="inline"
  />
</section>
```

## Progress

### 2026-01-22
- Scaffolded site with `pnpm new-site --slug hauler --industry hauler --register`
- Customized config with Quick Haul Co branding (blue #1d4ed8, orange #ea580c)
- Created Services page with quote request form
- Created Pricing page with tier pricing
- Created Book Now page with Cal.com embed (username: quickhaul, event: pickup)
- Deployed to Cloudflare Pages via Pulumi + wrangler
- Live at https://consult-hauler-dev.pages.dev
