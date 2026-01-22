# Infrastructure Setup Guide

Complete guide for setting up Consult infrastructure from scratch.

## Overview

Consult uses a split infrastructure model:

| Component | Platform | Purpose |
|-----------|----------|---------|
| Static Sites | Cloudflare Pages | Client marketing sites |
| Edge Workers | Cloudflare Workers | Form intake, webhooks |
| DNS/CDN | Cloudflare | DDoS protection, SSL |
| Django Backend | Hetzner Cloud | API, dashboard, admin |
| Database | Neon | Serverless Postgres |
| Secrets | Doppler | Centralized secret management |
| IaC | Pulumi | Infrastructure as code |

## Prerequisites

1. **Flox environment activated**: `flox activate`
2. **Accounts created** (free tiers work for dev):
   - [Doppler](https://dashboard.doppler.com) - secrets management
   - [Neon](https://console.neon.tech) - Postgres database
   - [Cloudflare](https://dash.cloudflare.com) - DNS, CDN, edge
   - [Hetzner Cloud](https://console.hetzner.cloud) - VPS hosting

## Quick Start

Run the interactive setup wizard:

```bash
just setup-infra
```

This guides you through:
1. Doppler access verification
2. Django secrets (SECRET_KEY, DEBUG, etc.)
3. Database connection (Neon)
4. Infrastructure secrets (Hetzner, Cloudflare)
5. Pulumi stack configuration

## Manual Setup

### Step 1: Doppler Configuration

Doppler is the single source of truth for all secrets.

```bash
# Install Doppler CLI (if not in Flox)
brew install dopplerhq/cli/doppler

# Login to Doppler
doppler login

# Setup project (creates .doppler.yaml)
doppler setup
# Select: consult → dev
```

Or use a service token:
```bash
# Get token from Doppler dashboard
export DOPPLER_TOKEN="dp.st.xxx"
```

### Step 2: Django Secrets

These are required for local development:

| Secret | Description | How to Set |
|--------|-------------|------------|
| `SECRET_KEY` | Django signing key | Auto-generate |
| `DEBUG` | Debug mode | `True` for dev |
| `ALLOWED_HOSTS` | Valid hostnames | `localhost,127.0.0.1` |

```bash
# Generate SECRET_KEY
doppler secrets set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

# Set DEBUG
doppler secrets set DEBUG=True

# Set ALLOWED_HOSTS
doppler secrets set ALLOWED_HOSTS="localhost,127.0.0.1"
```

### Step 3: Neon Database

1. Create a project at [console.neon.tech](https://console.neon.tech)
2. Get **two** connection strings:

**Pooled (for Django)** - has `-pooler` in hostname:
```
postgres://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
```

**Direct (for Workers)** - no `-pooler`:
```
postgres://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

```bash
doppler secrets set DATABASE_URL="postgres://...pooler..."
doppler secrets set NEON_DATABASE_URL="postgres://...direct..."
```

### Step 4: Intake Worker

```bash
# Generate API key for intake worker
doppler secrets set INTAKE_API_KEY="$(openssl rand -hex 32)"
```

### Step 5: Infrastructure Secrets (for Deployment)

These are needed to deploy with Pulumi:

#### Hetzner API Token

1. Go to [console.hetzner.cloud](https://console.hetzner.cloud)
2. Select/create a project
3. Security → API Tokens → Generate API Token
4. Name: `consult-pulumi`, Permissions: Read & Write

```bash
doppler secrets set HETZNER_API_TOKEN="your-token"
```

#### Cloudflare API Token

1. Go to [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Create Token → Use template "Edit zone DNS"
3. Add permissions:
   - Zone / DNS / Edit
   - Zone / Zone / Read
   - Account / Cloudflare Pages / Edit
   - Account / Workers Scripts / Edit
4. Zone Resources: Include → Specific zone → your-domain.com

```bash
doppler secrets set CLOUDFLARE_API_TOKEN="your-token"
```

#### Cloudflare IDs

Find these in your Cloudflare dashboard sidebar under "API":

```bash
doppler secrets set CLOUDFLARE_ACCOUNT_ID="your-account-id"
doppler secrets set CLOUDFLARE_ZONE_ID="your-zone-id"
doppler secrets set DOMAIN="yourdomain.com"
```

#### SSH Key

```bash
# Use existing key
doppler secrets set SSH_PUBLIC_KEY="$(cat ~/.ssh/id_ed25519.pub)"

# Or generate a new one
ssh-keygen -t ed25519 -f ~/.ssh/consult_deploy -N "" -C "consult-deploy"
doppler secrets set SSH_PUBLIC_KEY="$(cat ~/.ssh/consult_deploy.pub)"
```

### Step 6: Pulumi Setup

Initialize Pulumi stacks:

```bash
just infra-init
```

This creates:
- `infra/.venv` with Pulumi providers
- `dev` and `prod` stacks

Configure provider secrets:

```bash
cd infra

# Hetzner
pulumi config set --secret hcloud:token "$(doppler secrets get HETZNER_API_TOKEN --plain)" --stack dev

# Cloudflare
pulumi config set --secret cloudflare:apiToken "$(doppler secrets get CLOUDFLARE_API_TOKEN --plain)" --stack dev

# Stack config
pulumi config set cloudflare_account_id "$(doppler secrets get CLOUDFLARE_ACCOUNT_ID --plain)" --stack dev
pulumi config set cloudflare_zone_id "$(doppler secrets get CLOUDFLARE_ZONE_ID --plain)" --stack dev
pulumi config set domain "$(doppler secrets get DOMAIN --plain)" --stack dev
```

Or let the wizard do it:
```bash
just setup-infra
# Choose "Yes" for Pulumi configuration at the end
```

## Verification

### Check All Secrets

```bash
just check-secrets
```

### Test Local Development

```bash
just migrate        # Run migrations
just dev            # Start Django
# Visit http://localhost:8000/admin/
```

### Test Integration

```bash
just test-local     # Full integration test
```

### Preview Infrastructure

```bash
just infra-preview  # Show what would be created
```

## Deploying Infrastructure

Once configured:

```bash
# Preview changes
just infra-preview

# Apply changes (creates real resources!)
just infra-up

# Check outputs
just infra-outputs
```

## Secrets Reference

### Required for Local Development

| Secret | Purpose |
|--------|---------|
| `SECRET_KEY` | Django cryptographic signing |
| `DEBUG` | Debug mode (True/False) |
| `ALLOWED_HOSTS` | Valid hostnames |
| `DATABASE_URL` | Neon pooled connection |
| `NEON_DATABASE_URL` | Neon direct connection |
| `INTAKE_API_KEY` | Worker authentication |

### Required for Deployment

| Secret | Purpose |
|--------|---------|
| `HETZNER_API_TOKEN` | Pulumi → Hetzner |
| `CLOUDFLARE_API_TOKEN` | Pulumi → Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account |
| `CLOUDFLARE_ZONE_ID` | Domain zone |
| `DOMAIN` | Primary domain |
| `SSH_PUBLIC_KEY` | Server access |

### Optional (Feature-Specific)

| Secret | Purpose |
|--------|---------|
| `TWILIO_ACCOUNT_SID` | SMS/Voice |
| `TWILIO_AUTH_TOKEN` | SMS/Voice |
| `RESEND_API_KEY` | Email sending |

## Troubleshooting

### "Cannot access Doppler"

```bash
# Check token
echo $DOPPLER_TOKEN

# Re-authenticate
doppler login
doppler setup
```

### "Pulumi stack not found"

```bash
# Initialize stacks
just infra-init

# Or manually
cd infra
pulumi stack init dev
pulumi stack init prod
```

### "Provider authentication failed"

```bash
# Re-sync secrets to Pulumi
cd infra
pulumi config set --secret hcloud:token "$(doppler secrets get HETZNER_API_TOKEN --plain)" --stack dev
pulumi config set --secret cloudflare:apiToken "$(doppler secrets get CLOUDFLARE_API_TOKEN --plain)" --stack dev
```

### "SSH key not found on Hetzner"

The SSH key must be uploaded to Hetzner Cloud first:
1. Go to Security → SSH Keys in Hetzner console
2. Add your public key with name `consult-dev` (or `consult-prod`)

Or configure a different key name:
```bash
pulumi config set ssh_key_name "your-key-name" --stack dev
```

## Cost Estimate

| Resource | Dev | Prod |
|----------|-----|------|
| Hetzner CX22 | €4.50/mo | €9/mo (2x) |
| Hetzner Volume | €1/mo | €2.50/mo |
| Cloudflare | Free | Free-$20 |
| Neon | Free | $19/mo |
| Doppler | Free | Free |
| **Total** | **~$6/mo** | **~$50/mo** |
