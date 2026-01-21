# EP-005: Client Sites at Scale

**Status:** planned
**Last Updated:** 2026-01-21

## Goal

Deploy all 8 planned client sites, establish tooling for rapid site creation, and set up deployment automation. Prove the platform scales horizontally.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 005-A | Site scaffolding script | pending |
| 005-B | Deploy coffee-shop site | pending |
| 005-C | Deploy hauler site (+ Cal.com) | pending |
| 005-D | Deploy cleaning site | pending |
| 005-E | Deploy landscaper site | pending |
| 005-F | Deploy barber site | pending |
| 005-G | Deploy data-analytics site | pending |
| 005-H | Deploy web-dev site | pending |
| 005-I | Deploy local-agency site | pending |
| 005-J | CI/CD pipeline for sites | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Site creation | Script from template | Fast, consistent |
| Deployment | Cloudflare Pages | Already using, works well |
| CI/CD | GitHub Actions | Standard, integrates with CF |
| Domain pattern | {client}.consult.io | Consistent, easy DNS |

## Dependencies

- [x] EP-001 complete (template site works)
- [ ] Cloudflare account with Pages enabled
- [ ] DNS configured for *.consult.io
- [ ] Client branding assets gathered

## Site Matrix

| Site | Industry | Special Features |
|------|----------|------------------|
| coffee-shop | Food & Beverage | Menu, hours |
| hauler | Junk Removal | Cal.com booking, quote form |
| cleaning | Cleaning Services | Service packages |
| landscaper | Landscaping | Seasonal services |
| barber | Personal Services | Cal.com booking |
| data-analytics | B2B Software | Case studies, pricing tiers |
| web-dev | B2B Services | Portfolio, process |
| local-agency | B2B Services | Meta/self-referential |

## Progress Log

### 2026-01-21
- EP created
- Template site exists with DaisyUI + HTMX
- Next: create scaffolding script, then sites
