# 005-B: Deploy coffee-shop Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Deploy the first real client site for a coffee shop business.

## Acceptance Criteria

- [x] Site created at `sites/coffee-shop/`
- [x] Config: The Daily Grind, warm brown theme
- [x] Pages: Home, Menu, About, Contact
- [x] Contact form connected to intake worker
- [x] Deployed to Cloudflare Pages
- [x] Accessible at preview URL

## Deployed

**URL:** https://consult-coffee-shop-dev.pages.dev

## Implementation

### Branding
- Name: The Daily Grind
- Tagline: "Your neighborhood coffee destination"
- Colors: Brown (#78350f primary), Cream (#fef3c7 base)

### Services
- Coffee Bar
- Pastries
- Catering
- Event Space

### Theme (tailwind.config.ts)
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#78350f",      // Rich brown
      secondary: "#92400e",    // Amber brown
      accent: "#b45309",       // Warm amber
      "base-100": "#fef3c7",   // Cream background
      "base-content": "#78350f", // Brown text
    }
  }]
}
```

## Progress

### 2026-01-22
- Site already configured with The Daily Grind branding
- Registered in sites/registry.yaml
- Deployed via `just deploy-wizard dev`
- Live at https://consult-coffee-shop-dev.pages.dev
