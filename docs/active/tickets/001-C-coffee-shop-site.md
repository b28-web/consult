# 001-C: First Client Site (coffee-shop)

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** in-progress

## Summary

Scaffold the first real client site from template, customize for a coffee shop, deploy to Cloudflare Pages.

## Acceptance Criteria

- [x] sites/coffee-shop/ created from template
- [x] Config customized (name, colors, services)
- [x] DaisyUI theme uses warm brown palette
- [x] Contact form POSTs to intake worker (configured in config.ts)
- [x] Site builds successfully
- [ ] Site deploys to Cloudflare Pages
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

### 2026-01-21
- Copied template to sites/coffee-shop/
- Customized config.ts: "The Daily Grind" branding, 4 services (Coffee Bar, Pastries, Catering, Event Space)
- Updated tailwind.config.ts with warm brown (#78350f) / cream (#fef3c7) DaisyUI theme
- Updated wrangler.toml (project: consult-coffee-shop)
- Updated astro.config.mjs (site: thedailygrind.coffee)
- Added @consult/shared-ui workspace dependency
- Fixed template bug: changed output from deprecated "hybrid" to "static"
- Site builds successfully (2 pages: /, /contact)
- **Blocked**: Deployment requires Doppler/Neon setup (same as 001-B)
