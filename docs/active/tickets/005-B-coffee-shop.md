# 005-B: Deploy coffee-shop Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy the first real client site for a coffee shop business.

## Acceptance Criteria

- [ ] Site created at `sites/coffee-shop/`
- [ ] Config: The Daily Grind, warm brown theme
- [ ] Pages: Home, Menu, About, Contact
- [ ] Contact form connected to intake worker
- [ ] Deployed to Cloudflare Pages
- [ ] Accessible at coffee-shop.consult.io (or preview URL)

## Implementation Notes

Brand:
- Name: The Daily Grind
- Tagline: "Your neighborhood coffee destination"
- Colors: Brown (#78350f primary), Cream (#fef3c7)

Services:
- Coffee Bar
- Fresh Pastries
- Catering
- Event Space

DaisyUI theme:
```javascript
// tailwind.config.ts
daisyui: {
  themes: [{
    client: {
      primary: "#78350f",      // Warm brown
      secondary: "#92400e",
      accent: "#fef3c7",       // Cream
      neutral: "#1c1917",
      "base-100": "#fffbeb",   // Warm white
    }
  }]
}
```

## Progress

(Not started)
