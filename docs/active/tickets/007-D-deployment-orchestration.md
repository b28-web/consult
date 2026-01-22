# 007-D: Deployment Orchestration

**EP:** [EP-007-pulumi-infrastructure](../enhancement_proposals/EP-007-pulumi-infrastructure.md)
**Status:** completed

## Summary

Create unified deployment workflow that orchestrates Dagger (validation) and Pulumi (infrastructure) with Doppler as the single source of truth for all secrets.

## Acceptance Criteria

- [ ] `just deploy` runs full pipeline: validate → provision → deploy
- [ ] All secrets flow from Doppler (no duplication)
- [ ] Pulumi reads secrets from Doppler (not separate config)
- [ ] Dagger reads secrets from Doppler
- [ ] GitHub Actions uses single DOPPLER_TOKEN
- [ ] Clear separation: Doppler = secrets, Pulumi = infra state

## Unified Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOPPLER (Single Source)                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Project: consult                             │    │
│  │                                                                      │    │
│  │   Config: dev                    Config: prd                        │    │
│  │   ├── DATABASE_URL               ├── DATABASE_URL                   │    │
│  │   ├── SECRET_KEY                 ├── SECRET_KEY                     │    │
│  │   ├── NEON_DATABASE_URL          ├── NEON_DATABASE_URL              │    │
│  │   ├── INTAKE_API_KEY             ├── INTAKE_API_KEY                 │    │
│  │   ├── HETZNER_API_TOKEN          ├── HETZNER_API_TOKEN              │    │
│  │   ├── CLOUDFLARE_API_TOKEN       ├── CLOUDFLARE_API_TOKEN           │    │
│  │   ├── CLOUDFLARE_ACCOUNT_ID      ├── CLOUDFLARE_ACCOUNT_ID          │    │
│  │   └── SSH_PUBLIC_KEY             └── SSH_PUBLIC_KEY                 │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    │ doppler run --                          │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                        │
│              ┌──────────┐   ┌──────────┐   ┌──────────┐                     │
│              │  Dagger  │   │  Pulumi  │   │  Deploy  │                     │
│              │ Validate │   │  Infra   │   │  Apps    │                     │
│              └──────────┘   └──────────┘   └──────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Doppler Configuration

All secrets in one place, accessed via `doppler run --`:

```bash
# Doppler project structure
consult/
├── dev          # Local development
├── stg          # Staging (optional)
└── prd          # Production

# Secrets per config:
# App secrets
DATABASE_URL          # Neon pooled connection
NEON_DATABASE_URL     # Neon direct connection
SECRET_KEY            # Django secret
INTAKE_API_KEY        # Worker auth

# Infrastructure secrets
HETZNER_API_TOKEN     # Hetzner Cloud API
CLOUDFLARE_API_TOKEN  # Cloudflare API
CLOUDFLARE_ACCOUNT_ID # Cloudflare account
CLOUDFLARE_ZONE_ID    # DNS zone
SSH_PUBLIC_KEY        # Server SSH key
DOPPLER_TOKEN_DEPLOY  # Service token for servers
```

## Simplified Justfile

```just
# =============================================================================
# Unified Deployment (Doppler → Dagger → Pulumi)
# =============================================================================

# Full deployment pipeline
deploy ENV="dev":
    @echo "═══════════════════════════════════════"
    @echo "  Deploying to {{ENV}}"
    @echo "═══════════════════════════════════════"
    just deploy-validate {{ENV}}
    just deploy-infra {{ENV}}
    just deploy-apps {{ENV}}
    @echo ""
    @echo "  Deployment complete!"

# Step 1: Validate (Dagger)
deploy-validate ENV="dev":
    @echo "→ Running pre-deploy validation..."
    doppler run --config {{ENV}} -- dagger call pre-deploy

# Step 2: Provision infrastructure (Pulumi)
deploy-infra ENV="dev":
    @echo "→ Provisioning infrastructure..."
    cd infra && doppler run --config {{ENV}} -- pulumi up --stack {{ENV}} --yes

# Step 3: Deploy applications
deploy-apps ENV="dev":
    @echo "→ Deploying applications..."
    just deploy-worker-to {{ENV}}
    just deploy-sites-to {{ENV}}
    just deploy-django-to {{ENV}}

# Deploy worker to Cloudflare
deploy-worker-to ENV="dev":
    cd workers/intake && doppler run --config {{ENV}} -- pnpm wrangler deploy

# Deploy sites to Cloudflare Pages
deploy-sites-to ENV="dev":
    #!/usr/bin/env bash
    for site in sites/*/; do
        name=$(basename "$site")
        [[ "$name" == "_template" ]] && continue
        echo "  Deploying $name..."
        cd "$site" && doppler run --config {{ENV}} -- pnpm build && pnpm wrangler pages deploy dist
        cd - > /dev/null
    done

# Deploy Django to Hetzner
deploy-django-to ENV="dev":
    #!/usr/bin/env bash
    SERVER_IP=$(cd infra && doppler run --config {{ENV}} -- pulumi stack output django_server_ip --stack {{ENV}})
    echo "  Deploying Django to $SERVER_IP..."
    ssh ubuntu@$SERVER_IP 'cd /opt/consult && ./deploy.sh'

# Preview infrastructure changes
infra-preview ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi preview --stack {{ENV}}

# Show infrastructure outputs
infra-outputs ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi stack output --stack {{ENV}} --json
```

## Simplified GitHub Actions

`.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options: [dev, prd]

env:
  DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dopplerhq/cli-action@v3
      - uses: dagger/dagger-for-github@v6

      - name: Validate
        run: doppler run --config ${{ inputs.environment || 'dev' }} -- dagger call pre-deploy

  deploy-infra:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dopplerhq/cli-action@v3
      - uses: pulumi/actions@v5

      - name: Provision infrastructure
        run: |
          cd infra
          doppler run --config ${{ inputs.environment || 'dev' }} -- \
            pulumi up --stack ${{ inputs.environment || 'dev' }} --yes

  deploy-apps:
    needs: deploy-infra
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dopplerhq/cli-action@v3
      - uses: pnpm/action-setup@v2

      - name: Deploy worker
        run: |
          cd workers/intake
          pnpm install
          doppler run --config ${{ inputs.environment || 'dev' }} -- pnpm wrangler deploy

      - name: Deploy sites
        run: |
          for site in sites/*/; do
            name=$(basename "$site")
            [[ "$name" == "_template" ]] && continue
            cd "$site"
            pnpm install && pnpm build
            doppler run --config ${{ inputs.environment || 'dev' }} -- pnpm wrangler pages deploy dist
            cd - > /dev/null
          done

      - name: Deploy Django
        run: |
          SERVER_IP=$(cd infra && doppler run --config ${{ inputs.environment || 'dev' }} -- \
            pulumi stack output django_server_ip --stack ${{ inputs.environment || 'dev' }})
          ssh -o StrictHostKeyChecking=no ubuntu@$SERVER_IP 'cd /opt/consult && ./deploy.sh'
```

## Key Principles

1. **Doppler is the only secret store** - No secrets in Pulumi config, GitHub Secrets (except DOPPLER_TOKEN), or .env files

2. **`doppler run --config ENV --`** is the universal prefix - Every command that needs secrets uses this pattern

3. **Environment selection is explicit** - `dev` or `prd` passed through the chain

4. **Pulumi state is separate from secrets** - Pulumi manages infra state, Doppler manages secrets

5. **GitHub needs only one secret** - `DOPPLER_TOKEN` (service token with access to all configs)

## Progress

### 2026-01-22
- **Justfile updated**: Added unified deploy commands
  - `just deploy ENV` - Full pipeline: validate → provision → deploy
  - `just deploy-validate ENV` - Run Dagger pre-deploy checks
  - `just deploy-infra ENV` - Pulumi infrastructure provisioning
  - `just deploy-apps ENV` - Deploy worker, sites, Django
  - `just deploy-worker-to ENV` - Deploy intake worker to Cloudflare
  - `just deploy-sites-to ENV` - Deploy all sites to Pages
  - `just deploy-django-to ENV` - SSH deploy to Hetzner
  - Updated all `infra-*` commands to use Doppler

- **GitHub Actions deploy.yml rewritten**:
  - Environment selection: `dev` / `prd` (matches Doppler configs)
  - `provision-infra` job: Pulumi preview + up with Doppler secrets
  - `deploy-django` job: SSH to Hetzner server with deploy script
  - Single `DOPPLER_TOKEN` secret for all config access
  - Options to skip validation or infrastructure provisioning
