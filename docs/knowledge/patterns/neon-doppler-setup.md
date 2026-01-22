# Doppler Secrets Management

This guide covers all secrets management for Consult using Doppler as the single source of truth.

## Overview

Doppler is the **only** secrets store. All tools (Django, Dagger, Pulumi, CI/CD) access secrets via `doppler run --`.

| Service | Purpose | Environments |
|---------|---------|--------------|
| Doppler | All secrets | dev, prd |
| Neon | Serverless Postgres | dev, prod |
| Hetzner | Django hosting | dev, prod |
| Cloudflare | Edge (Workers, Pages) | dev, prod |

## Prerequisites

- Neon account: https://neon.tech (free tier works)
- Doppler account: https://doppler.com (free tier works)
- Doppler CLI installed: `brew install dopplerhq/cli/doppler`
- Cloudflare account (for Workers/Pages deployment)

## Step 1: Create Neon Project

1. Go to https://console.neon.tech
2. Click **New Project**
3. Settings:
   - Name: `consult` (or `consult-prod` for production)
   - Region: Pick closest to your users (e.g., `us-east-1`)
   - Postgres version: Latest (16+)
4. Click **Create Project**
5. Copy the connection string (you'll need it for Doppler)

### Connection Strings

Neon provides two connection string formats:

```
# Pooled (for Django - uses PgBouncer)
postgres://user:pass@ep-xxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require

# Direct (for Workers - uses Neon serverless driver)
postgres://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
```

- Use **pooled** for Django (`DATABASE_URL`)
- Use **direct** for Workers (`NEON_DATABASE_URL`)

### Create Production Branch (Optional)

For prod setup, use Neon branching:

1. In your Neon project, go to **Branches**
2. Click **New Branch**
3. Name: `prod` (or keep `main` as prod and create `dev` branch)
4. Each branch gets its own connection string

## Step 2: Create Doppler Project

1. Go to https://dashboard.doppler.com
2. Click **Create Project**
3. Name: `consult`
4. This creates three environments by default: `dev`, `stg`, `prd`

### Configure Secrets

For each environment, add these secrets:

#### Django Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-xxx` (dev) or generate secure key (prod) |
| `DEBUG` | Debug mode | `True` (dev) or `False` (prod) |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` (dev) or `consult.example.com` (prod) |
| `DATABASE_URL` | Pooled Neon connection | `postgres://...pooler.../neondb?sslmode=require` |

#### Worker Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `NEON_DATABASE_URL` | Direct Neon connection | `postgres://...neondb?sslmode=require` |
| `INTAKE_API_KEY` | API key for intake worker | Generate with `openssl rand -hex 32` |
| `TWILIO_AUTH_TOKEN` | Twilio webhook validation | From Twilio console (optional until EP-003) |

#### Cloudflare Secrets (for deployment)

| Secret | Description | Example |
|--------|-------------|---------|
| `CLOUDFLARE_API_TOKEN` | Wrangler deploy token | From Cloudflare dashboard |
| `CLOUDFLARE_ACCOUNT_ID` | Your CF account ID | Found in Cloudflare dashboard URL |

### Generate Django Secret Key

```bash
# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Or without Django installed:
openssl rand -hex 50
```

## Step 3: Connect Doppler CLI

```bash
# Login to Doppler
doppler login

# Set up project in this directory
doppler setup

# Select: consult > dev (for local development)
```

This creates `.doppler.yaml` (gitignored) linking this directory to your Doppler project.

## Step 4: Verify Setup

```bash
# Check Doppler can fetch secrets
doppler secrets

# Test Django connection
just migrate

# Test that Django starts
just dev
```

## Step 5: Deploy Workers with Secrets

Workers get secrets via `wrangler secret`:

```bash
# Push secrets from Doppler to Cloudflare Workers
doppler run -- wrangler secret put NEON_DATABASE_URL
doppler run -- wrangler secret put INTAKE_API_KEY

# Deploy the worker
doppler run -- wrangler deploy
```

Or use the automated setup:

```bash
just setup-infra
```

## Production Setup

To set up a production environment:

### 1. Create Neon Production Branch

```bash
# Via Neon console or CLI
neonctl branches create --name prod
```

### 2. Configure Doppler Production

1. Go to Doppler dashboard > consult > prd
2. Add all secrets with production values
3. Use the prod branch connection strings from Neon

### 3. Switch Environments

```bash
# Local dev (default)
doppler setup  # Select: dev

# Run with production config (careful!)
doppler run --config prd -- just migrate
```

## Quick Reference

### Complete Secrets Checklist

```
App Secrets (required for dev):
  [ ] SECRET_KEY           # Django cryptographic key
  [ ] DEBUG                # "True" or "False"
  [ ] ALLOWED_HOSTS        # Comma-separated hostnames
  [ ] DATABASE_URL         # Neon pooled connection (Django)
  [ ] NEON_DATABASE_URL    # Neon direct connection (Workers)
  [ ] INTAKE_API_KEY       # Worker authentication

Infrastructure Secrets (required for deploy):
  [ ] HETZNER_API_TOKEN    # Hetzner Cloud API
  [ ] CLOUDFLARE_API_TOKEN # Cloudflare API
  [ ] CLOUDFLARE_ACCOUNT_ID# Cloudflare account
  [ ] CLOUDFLARE_ZONE_ID   # DNS zone ID
  [ ] SSH_PUBLIC_KEY       # Server SSH access

Optional (for specific features):
  [ ] TWILIO_AUTH_TOKEN    # SMS/Voice (EP-003)
  [ ] TWILIO_ACCOUNT_SID   # SMS/Voice (EP-003)
  [ ] RESEND_API_KEY       # Email (EP-003)
```

### Unified Access Pattern

All tools use the same pattern:

```bash
# Local development
doppler run -- just dev

# Specific environment
doppler run --config prd -- pulumi up

# In CI/CD (DOPPLER_TOKEN set in env)
doppler run --config $ENV -- dagger call pre-deploy
```

### Common Commands

```bash
# View all secrets (masked)
doppler secrets

# View a specific secret
doppler secrets get DATABASE_URL

# Run command with secrets
doppler run -- <command>

# Check setup
just setup-infra
```

### Troubleshooting

**"No Doppler token found"**
```bash
doppler login
doppler setup
```

**"DATABASE_URL not set"**
- Check Doppler has the secret: `doppler secrets`
- Ensure you're in the right config: `doppler configure`

**"Connection refused" on Neon**
- Check the connection string has `?sslmode=require`
- Ensure you're using the pooled URL for Django

**Worker deploy fails**
- Ensure Cloudflare secrets are set: `wrangler secret list`
- Check account ID matches: `wrangler whoami`
