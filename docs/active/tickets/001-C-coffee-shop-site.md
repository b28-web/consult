# 001-C: First Client Site (coffee-shop)

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** pending

## Summary

Scaffold the first real client site from template, customize for a coffee shop, deploy to Cloudflare Pages.

## Acceptance Criteria

- [ ] sites/coffee-shop/ created from template
- [ ] Config customized (name, colors, services)
- [ ] DaisyUI theme uses warm brown palette
- [ ] Contact form POSTs to intake worker
- [ ] Site builds and deploys to Cloudflare Pages
- [ ] Form submission creates row in database

## Implementation Notes

```
sites/coffee-shop/                # Copy from _template
├── src/config.ts                 # Coffee shop branding
├── tailwind.config.ts            # Brown/cream theme
├── wrangler.toml                 # Project: consult-coffee-shop
└── astro.config.mjs              # Site URL
```

Fictional business:
- Name: The Daily Grind
- Services: Coffee Bar, Pastries, Catering, Event Space
- Colors: Brown (#78350f), Cream (#fef3c7)

## Progress

(Not started - depends on 001-A and 001-B)
