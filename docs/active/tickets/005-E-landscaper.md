# 005-E: Deploy landscaper Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy landscaping services site with seasonal service offerings.

## Acceptance Criteria

- [ ] Site created at `sites/landscaper/`
- [ ] Config: Green Thumb Landscaping, natural earth tones
- [ ] Pages: Home, Services, Gallery, Contact
- [ ] Seasonal services highlighted
- [ ] Photo gallery of past work
- [ ] Quote request form
- [ ] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Green Thumb Landscaping
- Tagline: "Transform your outdoor space"
- Colors: Forest green (#166534), Earth brown (#78350f), Sky blue (#0284c7)

Services:
- Lawn Maintenance (mowing, edging, fertilization)
- Landscape Design & Installation
- Tree & Shrub Care
- Irrigation Systems
- Hardscaping (patios, walkways)
- Seasonal Cleanup

Seasonal Highlights:
```typescript
seasons: {
  spring: ["Cleanup", "Mulching", "Planting", "Aeration"],
  summer: ["Mowing", "Watering", "Pest Control", "Trimming"],
  fall: ["Leaf Removal", "Winterization", "Final Mow", "Seeding"],
  winter: ["Snow Removal", "Planning", "Tree Pruning"],
}
```

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#166534",      // Forest green
      secondary: "#78350f",    // Earth brown
      accent: "#0284c7",       // Sky blue
      "base-100": "#f0fdf4",   // Light green tint
      "base-content": "#14532d", // Dark green text
    }
  }]
}
```

## Progress

(Not started)
