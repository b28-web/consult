# Deployment Guide

This guide covers deploying Consult to production using the unified deployment pipeline.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT FLOW                                 │
│                                                                              │
│    just deploy ENV          GitHub Actions              Manual               │
│         │                        │                         │                 │
│         ▼                        ▼                         ▼                 │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                         DOPPLER                                   │     │
│    │                   (Single Secret Store)                           │     │
│    │                                                                   │     │
│    │     dev config              prd config                           │     │
│    │     ├── DATABASE_URL        ├── DATABASE_URL                     │     │
│    │     ├── HETZNER_TOKEN       ├── HETZNER_TOKEN                    │     │
│    │     └── ...                 └── ...                              │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│              doppler run --config ENV --                                     │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         ▼                          ▼                          ▼             │
│    ┌──────────┐            ┌──────────────┐            ┌──────────┐        │
│    │  Dagger  │            │    Pulumi    │            │  Deploy  │        │
│    │ Validate │────────────│    Infra     │────────────│   Apps   │        │
│    └──────────┘            └──────────────┘            └──────────┘        │
│                                                              │               │
│                                          ┌───────────────────┼───────────┐  │
│                                          ▼                   ▼           ▼  │
│                                   ┌──────────┐        ┌──────────┐ ┌──────┐│
│                                   │ Cloudflare│       │ Cloudflare│ │Hetzner│
│                                   │  Worker  │        │   Pages  │ │Django││
│                                   └──────────┘        └──────────┘ └──────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Doppler Access

All secrets are managed in Doppler. You need a service token:

```bash
# Check if you have Doppler access
doppler secrets --only-names

# If not, get a token from https://dashboard.doppler.com
# Project: consult → Access → Service Tokens → Generate
export DOPPLER_TOKEN="dp.st.xxx"
```

### 2. Required Secrets in Doppler

| Secret | Description | Required For |
|--------|-------------|--------------|
| `DATABASE_URL` | Neon pooled connection | Django |
| `NEON_DATABASE_URL` | Neon direct connection | Workers |
| `SECRET_KEY` | Django secret key | Django |
| `INTAKE_API_KEY` | Worker auth key | Workers |
| `HETZNER_API_TOKEN` | Hetzner Cloud API | Infrastructure |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API | Infrastructure, Deploy |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account | Infrastructure |
| `CLOUDFLARE_ZONE_ID` | DNS zone ID | Infrastructure |
| `SSH_PUBLIC_KEY` | Server SSH key | Infrastructure |
| `SSH_PRIVATE_KEY` | Server SSH key (CI only) | Django deploy |

Run `just setup-infra` for an interactive setup wizard.

### 3. Pulumi State Backend

Pulumi state is stored in Pulumi Cloud (default) or can be configured for S3/local.

```bash
# Login to Pulumi Cloud
pulumi login

# Or use local state (development only)
pulumi login --local
```

## Local Deployment

### Full Pipeline

Deploy everything: validation → infrastructure → applications.

```bash
# Deploy to dev environment
just deploy dev

# Deploy to production
just deploy prd
```

### Step-by-Step

Run individual stages:

```bash
# 1. Validate (runs Dagger pre-deploy checks)
just deploy-validate dev

# 2. Provision infrastructure (Pulumi)
just deploy-infra dev

# 3. Deploy applications
just deploy-apps dev
```

### Deploy Specific Components

```bash
# Deploy only the intake worker
just deploy-worker-to dev

# Deploy only static sites
just deploy-sites-to dev

# Deploy only Django
just deploy-django-to dev
```

## Site Registry & Deploy Wizard

Client sites are managed through a central registry at `sites/registry.yaml`.

### Registry Format

```yaml
sites:
  coffee-shop:
    ready: true      # Will be deployed
    dev: {}
    prod:
      domain: coffee.example.com  # Custom domain (optional)

  future-site:
    ready: false     # Won't be deployed yet
    dev: {}
```

### Site Management Commands

```bash
# List all sites and their registry status
just list-sites

# Register a new site for deployment
just register-site my-site

# Interactive deploy wizard (recommended)
just deploy-wizard dev
```

### Deploy Wizard Workflow

The `just deploy-wizard` command provides an interactive deployment experience:

1. Reads `sites/registry.yaml` to find ready sites
2. Runs `pulumi preview` to check infrastructure
3. Prompts to create/update Cloudflare Pages projects
4. Builds and deploys each ready site

```bash
# Full interactive wizard
just deploy-wizard dev

# What it does:
#   1. Finds: coffee-shop (ready=true)
#   2. Pulumi: Creates consult-coffee-shop-dev Pages project
#   3. Deploys: Builds and pushes to Cloudflare Pages
```

### Creating New Sites

```bash
# Create site with scaffolding script
pnpm new-site --slug my-site --name "My Site" --tagline "Best site" --industry saas

# Or create + register in one step
pnpm new-site --slug my-site --name "My Site" --tagline "Best site" --industry saas --register

# Then deploy
just deploy-wizard dev
```

### Infrastructure Management

```bash
# Preview infrastructure changes
just infra-preview dev

# Show current infrastructure outputs
just infra-outputs dev

# Refresh state from cloud providers
just infra-refresh dev

# Destroy infrastructure (careful!)
just infra-destroy dev
```

## CI/CD Deployment

### GitHub Actions

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that can be triggered manually:

1. Go to **Actions** → **Deploy**
2. Click **Run workflow**
3. Select environment: `dev` or `prd`
4. Optionally skip validation or infrastructure

### GitHub Secrets Required

Only one secret is needed:

| Secret | Value |
|--------|-------|
| `DOPPLER_TOKEN` | Service token with access to all configs |

Create a Doppler service token with access to both `dev` and `prd` configs:
1. Go to https://dashboard.doppler.com
2. Project: `consult` → Access → Service Tokens
3. Generate token with access to all configs
4. Add to GitHub: Settings → Secrets → Actions → New secret

### CI Commands

For automation scripts or custom CI pipelines:

```bash
# Full CI deploy (validate → infra → apps)
just deploy-ci dev

# Apps only (skip validation and infra)
just deploy-ci-apps dev

# Skip validation (use with caution)
just deploy-ci-no-validate dev

# Validate only (for PR checks)
just deploy-ci-validate
```

### Example: GitLab CI

```yaml
deploy-dev:
  stage: deploy
  script:
    - just deploy-ci dev
  environment:
    name: development
  only:
    - main

deploy-prod:
  stage: deploy
  script:
    - just deploy-ci prd
  environment:
    name: production
  when: manual
  only:
    - main
```

### Example: Shell Script

```bash
#!/bin/bash
set -euo pipefail

# Ensure DOPPLER_TOKEN is set
if [ -z "${DOPPLER_TOKEN:-}" ]; then
    echo "Error: DOPPLER_TOKEN not set"
    exit 1
fi

# Deploy to dev
just deploy-ci dev
```

## Environment Configuration

### Doppler Configs

| Config | Purpose |
|--------|---------|
| `dev` | Development/staging environment |
| `prd` | Production environment |

### Switching Environments

```bash
# Switch Doppler default config
just doppler-env dev
just doppler-env prd

# Or specify per-command
just deploy dev
just deploy prd
```

## Troubleshooting

### Doppler Access Issues

```bash
# Check current config
doppler configure

# Verify token works
doppler secrets --only-names

# Re-authenticate
unset DOPPLER_TOKEN
doppler login
```

### Pulumi Issues

```bash
# Check stack state
cd infra && pulumi stack

# Refresh state from providers
just infra-refresh dev

# Export state for debugging
cd infra && pulumi stack export > state.json
```

### SSH to Server

```bash
# Get server IP
just infra-outputs dev | jq -r '.django_server_ip'

# SSH manually
ssh ubuntu@<server-ip>

# Check deploy logs on server
ssh ubuntu@<server-ip> 'journalctl -u consult -f'
```

### Validation Failures

```bash
# Run validation with verbose output
cd dagger && dagger call pre-deploy --source=.. 2>&1 | tee validation.log

# Run specific checks
just dagger-lint
just dagger-typecheck
just dagger-test
```

## Rollback

### Quick Rollback (Apps Only)

If you need to rollback application code:

```bash
# On the server
ssh ubuntu@<server-ip>
cd /opt/consult
git checkout <previous-commit>
./deploy.sh
```

### Infrastructure Rollback

Pulumi maintains state history:

```bash
cd infra

# View history
pulumi stack history

# Rollback to previous state (creates new deployment)
pulumi up --target-replace <resource-urn>
```

## Security Notes

1. **Never commit secrets** - All secrets live in Doppler
2. **Use separate tokens** - Dev and prod should use different Doppler tokens in production
3. **Rotate secrets regularly** - Especially after team changes
4. **Audit access** - Check Doppler access logs periodically

## Quick Reference

| Command | Description |
|---------|-------------|
| `just deploy dev` | Full deploy to dev |
| `just deploy prd` | Full deploy to production |
| `just deploy-wizard dev` | Interactive site deploy wizard |
| `just list-sites` | Show all sites and registry status |
| `just register-site SLUG` | Register site for deployment |
| `just deploy-ci dev` | CI deploy (non-interactive) |
| `just deploy-ci-apps dev` | CI deploy apps only |
| `just deploy-ci-validate` | Run validation only |
| `just infra-preview dev` | Preview infra changes |
| `just infra-outputs dev` | Show infra outputs |
| `just setup-infra` | Interactive setup wizard |
| `pnpm new-site --register` | Create + register new site |
