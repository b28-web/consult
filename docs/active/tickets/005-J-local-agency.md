# 005-I: Deploy local-agency Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy local marketing agency site (meta/self-referential - showcases Consult platform capabilities).

## Acceptance Criteria

- [ ] Site created at `sites/local-agency/`
- [ ] Config: Consult Local, professional blue/slate theme
- [ ] Pages: Home, Services, How It Works, Pricing, Contact
- [ ] Showcases the Consult platform itself
- [ ] Client testimonials
- [ ] Onboarding inquiry form
- [ ] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: Consult Local
- Tagline: "Your business, online in days"
- Colors: Professional blue (#1e40af), Slate (#475569), White

This is a meta site - it's a demo of the Consult platform marketing itself as a local agency that builds sites for small businesses.

Services:
- Website Design & Development
- Online Booking Integration
- Contact Form & Lead Capture
- Mobile-Optimized Design
- SEO Fundamentals
- Ongoing Support

How It Works:
1. Discovery Call - Tell us about your business
2. Design - We create your custom site
3. Review - You provide feedback
4. Launch - Go live in days, not months
5. Grow - We help you get found online

Pricing Tiers:
```typescript
pricing: [
  {
    name: "Starter",
    price: "$999",
    setup: "one-time",
    features: ["5-page website", "Mobile responsive", "Contact form", "Basic SEO"],
  },
  {
    name: "Professional",
    price: "$1,999",
    setup: "one-time",
    features: ["10-page website", "Booking integration", "Lead capture", "Local SEO", "Analytics"],
    highlighted: true,
  },
  {
    name: "Premium",
    price: "$3,499",
    setup: "one-time",
    features: ["Unlimited pages", "Custom features", "Priority support", "Monthly updates"],
  },
]
```

Testimonials:
- "Had my coffee shop website up in 3 days!" - The Daily Grind
- "Booking integration changed our business" - Quick Haul Co
- "Finally a website that looks professional" - Classic Cuts

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#1e40af",      // Blue
      secondary: "#475569",    // Slate
      accent: "#0ea5e9",       // Sky blue
      neutral: "#1e293b",      // Dark slate
      "base-100": "#ffffff",
      "base-content": "#1e293b",
    }
  }]
}
```

## Progress

(Not started)
