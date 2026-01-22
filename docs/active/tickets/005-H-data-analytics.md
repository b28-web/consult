# 005-G: Deploy data-analytics Site

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Deploy B2B data analytics SaaS marketing site with case studies and pricing tiers.

## Acceptance Criteria

- [ ] Site created at `sites/data-analytics/`
- [ ] Config: DataFlow Analytics, modern tech blue/purple theme
- [ ] Pages: Home, Features, Pricing, Case Studies, Contact
- [ ] Pricing tiers displayed
- [ ] Case studies with metrics
- [ ] Demo request form
- [ ] Deployed to Cloudflare Pages

## Implementation Notes

Brand:
- Name: DataFlow Analytics
- Tagline: "Turn data into decisions"
- Colors: Tech blue (#2563eb), Purple accent (#7c3aed), Dark (#0f172a)

Features:
- Real-time Dashboards
- Custom Reports
- Data Integration (100+ connectors)
- AI-Powered Insights
- Team Collaboration
- Enterprise Security

Pricing Tiers:
```typescript
pricing: [
  {
    name: "Starter",
    price: "$49/mo",
    features: ["5 dashboards", "10 data sources", "Email support"],
  },
  {
    name: "Professional",
    price: "$149/mo",
    features: ["Unlimited dashboards", "50 data sources", "AI insights", "Priority support"],
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    features: ["Everything in Pro", "Unlimited sources", "SSO", "Dedicated support", "SLA"],
  },
]
```

Case Studies:
- "How Acme Corp reduced reporting time by 80%"
- "TechStart's journey to data-driven decisions"
- "Enterprise scale: 10M rows processed daily"

DaisyUI theme:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "#2563eb",      // Blue
      secondary: "#7c3aed",    // Purple
      accent: "#06b6d4",       // Cyan
      neutral: "#0f172a",      // Dark slate
      "base-100": "#ffffff",
      "base-content": "#0f172a",
    }
  }]
}
```

## Progress

(Not started)
