# 005-D: Deploy cleaning Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Deploy cleaning services site with service packages and booking.

## Acceptance Criteria

- [x] Site created at `sites/cleaning/`
- [x] Config: Sparkle Clean Co, fresh green/white theme
- [x] Pages: Home, Services, Pricing, Contact
- [x] Service packages displayed with pricing tiers
- [x] Quote request form
- [x] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Sparkle Clean Co
- Tagline: "Professional cleaning, sparkling results"
- Colors: Fresh green (#059669), Clean white (#f0fdf4)

Services:
- Regular House Cleaning
- Deep Cleaning
- Move In/Out Cleaning
- Office Cleaning
- Post-Construction Cleanup

Service Packages:
```typescript
packages: [
  { name: "Basic", frequency: "Weekly", rooms: "up to 3", price: "$99" },
  { name: "Standard", frequency: "Weekly", rooms: "up to 5", price: "$149" },
  { name: "Premium", frequency: "Weekly", rooms: "Whole home", price: "$199" },
]
```

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#059669",      // Emerald green
      secondary: "#10b981",    // Light green
      accent: "#34d399",       // Bright green
      "base-100": "#f0fdf4",   // Mint white
      "base-content": "#064e3b", // Dark green text
    }
  }]
}
```

## Progress

### 2026-01-22
- Scaffolded site with `pnpm new-site --slug cleaning --industry cleaning --register`
- Customized theme with fresh green (#059669) and mint white (#f0fdf4)
- Created Services page with 5 cleaning services
- Created Pricing page with 3 tiers (Basic $99, Standard $149, Premium $199) + frequency discounts + add-ons
- Deployed to Cloudflare Pages
- Live at https://consult-cleaning-dev.pages.dev
