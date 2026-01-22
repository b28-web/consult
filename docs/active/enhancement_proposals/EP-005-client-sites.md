# EP-005: Client Sites at Scale

**Status:** active
**Last Updated:** 2026-01-22

## Goal

Deploy all 8 planned client sites, establish tooling for rapid site creation, and set up deployment automation. Prove the platform scales horizontally.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 005-A | Site scaffolding + registry system | complete |
| 005-B | Deploy coffee-shop site | complete |
| 005-C | Deploy hauler site (+ Cal.com) | complete |
| 005-D | Deploy cleaning site | complete |
| 005-E | Deploy landscaper site | complete |
| **005-F** | **Template hardening (mobile, CSS)** | **pending** |
| 005-G | Deploy barber site | pending |
| 005-H | Deploy data-analytics site | pending |
| 005-I | Deploy web-dev site | pending |
| 005-J | Deploy local-agency site | pending |
| 005-K | CI/CD pipeline for sites | pending |

> **Note:** 005-F inserted to consolidate template fixes before deploying more sites.
> Reduces O(n) maintenance burden by fixing issues once in template.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Site creation | Script from template | Fast, consistent |
| Site registry | `sites/registry.yaml` | Central, version-controlled, pull-based |
| Deployment | Cloudflare Pages | Already using, works well |
| Deploy tooling | `just deploy-wizard` | Interactive, validates infra first |
| CI/CD | GitHub Actions | Standard, integrates with CF |
| Domain pattern | {client}.consult.io | Consistent, easy DNS |

## Site Registry System

Sites are managed through a central registry at `sites/registry.yaml`. This enables:
- **Pull-based deployment**: Only sites marked `ready: true` are deployed
- **Infrastructure-as-code**: Pulumi reads registry to create CF Pages projects
- **Interactive wizard**: `just deploy-wizard` validates and deploys

### Registry Format

```yaml
sites:
  coffee-shop:
    ready: true      # Will be deployed
    dev: {}
    prod:
      domain: coffee.example.com  # Custom domain (optional)
```

### Commands

| Command | Purpose |
|---------|---------|
| `just list-sites` | Show all sites and registry status |
| `just register-site SLUG` | Add site to registry |
| `just deploy-wizard ENV` | Interactive deploy with infra validation |
| `pnpm new-site --register` | Create + register in one step |

### Workflow

```
1. Create:    pnpm new-site --slug foo --register
2. Customize: Edit sites/foo/src/config.ts
3. Deploy:    just deploy-wizard dev
```

## Dependencies

- [x] EP-001 complete (template site works)
- [ ] Cloudflare account with Pages enabled
- [ ] DNS configured for *.consult.io
- [ ] Client branding assets gathered

## Related: EP-008 Restaurant POS Integration

**Note:** This EP covers simple service and B2B sites using the standard `_template/`.

Full **restaurant** sites with POS integration (Toast/Clover/Square), real-time menu sync, 86'd item handling, and online ordering are handled by **[EP-008](EP-008-restaurant-pos-integration.md)**, which creates a separate `_template-restaurant/` with extended functionality.

The `coffee-shop` site in this EP is a **simple cafe** (static menu page, hours display) - not a full restaurant with POS integration.

## Site Matrix

| Site | Industry | Special Features | Notes |
|------|----------|------------------|-------|
| coffee-shop | Cafe | Static menu, hours | Simple F&B, no POS |
| hauler | Junk Removal | Cal.com booking, quote form | |
| cleaning | Cleaning Services | Service packages | |
| landscaper | Landscaping | Seasonal services | |
| barber | Personal Services | Cal.com booking | |
| data-analytics | B2B Software | Case studies, pricing tiers | |
| web-dev | B2B Services | Portfolio, process | |
| local-agency | B2B Services | Meta/self-referential | |

## Progress Log

### 2026-01-22 (CSS fix + reprioritization)
- Fixed Tailwind v4 + DaisyUI integration (added `@config` directive)
- Rebuilt and redeployed all 4 sites
- Created 005-F (template hardening) to address mobile responsiveness
- Shifted remaining site deploys to 005-G through 005-J

### 2026-01-22 (landscaper site)
- Deployed landscaper site with seasonal services
- Live at https://consult-landscaper-dev.pages.dev
- Features: Services page with seasonal highlights, Gallery page, maintenance plans
- 005-E complete

### 2026-01-22 (cleaning site)
- Deployed cleaning site with service packages
- Live at https://consult-cleaning-dev.pages.dev
- Features: Services page, Pricing page with 3 tiers + frequency discounts
- 005-D complete

### 2026-01-22 (hauler site)
- Deployed hauler site with Cal.com booking integration
- Live at https://consult-hauler-dev.pages.dev
- Features: Services page with quote form, Pricing page, Book Now with Cal.com embed
- 005-C complete

### 2026-01-22 (deployment)
- Deployed coffee-shop site via `just deploy-wizard dev`
- Live at https://consult-coffee-shop-dev.pages.dev
- 005-B complete

### 2026-01-22 (registry)
- Built site registry system:
  - Created `sites/registry.yaml` as central deployment registry
  - Updated Pulumi `pages.py` to read from registry
  - Added `just list-sites`, `just register-site`, `just deploy-wizard` commands
  - Added `--register` flag to scaffolding script
- Tested full workflow with coffee-shop site
- coffee-shop registered and ready to deploy

### 2026-01-22
- Completed 005-A: Site scaffolding script
- Created `scripts/new-site.sh` with industry presets (incl. restaurant for future EP-008)
- Added `pnpm new-site` command
- Clarified relationship with EP-008 (restaurant POS sites)

### 2026-01-21
- EP created
- Template site exists with DaisyUI + HTMX
- Next: create scaffolding script, then sites
