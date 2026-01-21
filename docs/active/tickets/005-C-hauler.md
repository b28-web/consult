# 005-C: Deploy hauler Site (+ Cal.com)

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy junk hauler site with Cal.com booking integration.

## Acceptance Criteria

- [ ] Site created at `sites/hauler/`
- [ ] Config: Quick Haul Co, bold blue/orange theme
- [ ] Pages: Home, Services, Pricing, Book Now, Contact
- [ ] Cal.com embed on Book Now page
- [ ] Quote request form on Services page
- [ ] Deployed to Cloudflare Pages

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

(Not started)
