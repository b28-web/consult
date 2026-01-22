# 005-A: Site Scaffolding + Registry System

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Create tooling to scaffold new client sites and manage deployment through a central registry.

## Acceptance Criteria

### Scaffolding Script
- [x] `scripts/new-site.sh` or `pnpm new-site` command
- [x] Prompts for: slug, name, tagline, industry
- [x] Copies `sites/_template/` to `sites/{slug}/`
- [x] Updates config.ts with provided values
- [x] Updates wrangler.toml with project name
- [x] Sets up reasonable defaults based on industry
- [x] Prints next steps (customize, deploy)

### Site Registry System
- [x] Central registry file at `sites/registry.yaml`
- [x] `just list-sites` - show all sites and status
- [x] `just register-site SLUG` - add site to registry
- [x] `just deploy-wizard ENV` - interactive deploy with validation
- [x] `--register` flag for scaffolding script
- [x] Pulumi reads registry to create CF Pages projects

## Implementation

### Files Created/Modified

| File | Purpose |
|------|---------|
| `scripts/new-site.sh` | Site scaffolding script |
| `sites/registry.yaml` | Central deployment registry |
| `infra/src/cloudflare/pages.py` | Updated to read from registry |
| `infra/requirements.txt` | Added pyyaml dependency |
| `justfile` | Added registry management commands |
| `package.json` | Added `new-site` script |

### Scaffolding Script

```bash
# Interactive
./scripts/new-site.sh

# Non-interactive
./scripts/new-site.sh --slug acme --name "Acme Inc" --tagline "Best widgets" --industry saas

# With auto-registration
./scripts/new-site.sh --slug acme ... --register
```

**Industries supported:** coffee-shop, restaurant, hauler, cleaning, landscaper, barber, saas, agency

### Registry Format

```yaml
# sites/registry.yaml
sites:
  coffee-shop:
    ready: true      # Will be deployed
    dev: {}
    prod:
      domain: coffee.example.com
```

### Deploy Workflow

```bash
# 1. Create site
pnpm new-site --slug foo --name "Foo" --tagline "Best Foo" --industry saas --register

# 2. Customize
cd sites/foo && edit src/config.ts

# 3. Deploy
just deploy-wizard dev
```

The deploy wizard:
1. Reads `sites/registry.yaml`
2. Finds sites with `ready: true`
3. Runs `pulumi preview` to check infrastructure
4. Prompts to apply infrastructure changes
5. Builds and deploys each ready site

## Progress

### 2026-01-22
- Created `scripts/new-site.sh` with full functionality
- Added `pnpm new-site` command to root package.json
- Tested scaffolding with multiple industries
- Built site registry system:
  - `sites/registry.yaml` as source of truth
  - Pulumi integration (reads registry for CF Pages)
  - `just list-sites`, `register-site`, `deploy-wizard` commands
  - `--register` flag for scaffolding
- Tested full workflow with coffee-shop site
- All acceptance criteria met
