# 005-H: Deploy web-dev Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy web development agency site with portfolio and process showcase.

## Acceptance Criteria

- [ ] Site created at `sites/web-dev/`
- [ ] Config: Pixel Perfect Studios, creative gradient theme
- [ ] Pages: Home, Services, Portfolio, Process, Contact
- [ ] Portfolio gallery with project showcases
- [ ] Development process timeline
- [ ] Project inquiry form
- [ ] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Pixel Perfect Studios
- Tagline: "Crafting digital experiences"
- Colors: Gradient primary (pink #ec4899 → purple #8b5cf6), Dark (#18181b)

Services:
- Custom Web Development
- E-commerce Solutions
- Web Application Development
- UI/UX Design
- Website Maintenance
- Performance Optimization

Portfolio Projects:
```typescript
portfolio: [
  {
    name: "E-commerce Platform",
    client: "Fashion Brand",
    tech: ["Next.js", "Stripe", "Sanity"],
    image: "/portfolio/ecommerce.jpg",
  },
  {
    name: "SaaS Dashboard",
    client: "FinTech Startup",
    tech: ["React", "D3.js", "Node.js"],
    image: "/portfolio/saas.jpg",
  },
  {
    name: "Corporate Website",
    client: "Law Firm",
    tech: ["Astro", "Tailwind", "Contentful"],
    image: "/portfolio/corporate.jpg",
  },
]
```

Process Steps:
1. Discovery - Understand your goals and requirements
2. Design - Create wireframes and visual designs
3. Development - Build with modern technologies
4. Testing - Ensure quality across devices
5. Launch - Deploy and monitor
6. Support - Ongoing maintenance and updates

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#ec4899",      // Pink
      secondary: "#8b5cf6",    // Purple
      accent: "#06b6d4",       // Cyan
      neutral: "#18181b",      // Zinc dark
      "base-100": "#fafafa",   // Light gray
      "base-content": "#18181b",
    }
  }]
}
```

## Progress

(Not started)
