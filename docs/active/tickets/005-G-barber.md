# 005-F: Deploy barber Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Deploy barbershop site with Cal.com booking integration.

## Acceptance Criteria

- [x] Site created at `sites/barber/`
- [x] Config: Classic Cuts Barbershop, classic black/gold theme
- [x] Pages: Home, Services, Book Now, Contact
- [x] Cal.com embed for appointment booking
- [x] Service menu with prices
- [x] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Classic Cuts Barbershop
- Tagline: "Where tradition meets style"
- Colors: Classic black (#171717), Gold accent (#d97706), Cream (#fef3c7)

Services:
- Classic Haircut ($25)
- Fade/Taper ($30)
- Beard Trim ($15)
- Hot Towel Shave ($35)
- Haircut + Beard Combo ($40)
- Kids Cut ($18)

Cal.com config:
```typescript
// src/config.ts
calcom: {
  username: "classiccuts",
  eventSlug: "haircut",
  brandColor: "d97706",
}
```

Book Now page with Cal.com:
```astro
---
import CalEmbed from '@/components/CalEmbed.astro';
import { config } from '@/config';
---
<section>
  <h1>Book Your Appointment</h1>
  <p>Select a service and time that works for you.</p>
  <CalEmbed
    username={config.calcom.username}
    eventSlug={config.calcom.eventSlug}
    mode="inline"
  />
</section>
```

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#171717",      // Black
      "primary-content": "#fef3c7", // Cream text
      secondary: "#d97706",    // Gold
      accent: "#fbbf24",       // Bright gold
      "base-100": "#fef3c7",   // Cream background
      "base-content": "#171717", // Black text
    }
  }]
}
```

## Progress

### 2026-01-22
- Created site from template with `--industry barber`
- Updated config with 6 services with prices
- Configured DaisyUI black/gold theme
- Created Book Now page with Cal.com embed
- Created Services page with price menu
- Updated index.astro with barbershop branding
- Deployed to Cloudflare Pages
- **Live at**: https://consult-barber-dev.pages.dev
