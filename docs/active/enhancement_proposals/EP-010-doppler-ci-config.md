# EP-010: Doppler CI Configuration

**Status:** active
**Last Updated:** 2026-01-22

## Problem

The Deploy Sites CI workflow fails because Doppler is misconfigured:

```
Doppler Error: This token does not have access to requested config 'dev'
```

**Root cause:** During initial setup, Doppler was configured with `dev_personal` instead of `dev`. The CI workflows expect standard config names (`dev`, `prd`) that match the environment naming convention.

## Goal

Set up proper Doppler configurations for CI/CD:
- Create `dev` and `prd` configs in Doppler project `b28-consult`
- Update GitHub Actions DOPPLER_TOKEN to access these configs
- Verify all CI workflows can deploy successfully

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 010-A | Create dev/prd configs in Doppler | pending |
| 010-B | Update GitHub DOPPLER_TOKEN | pending |
| 010-C | Verify Deploy Sites workflow | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Config naming | `dev`, `prd` | Matches workflow expectations, standard convention |
| Token type | Service Account | Scoped access, can be rotated independently |
| Secret location | GitHub Actions secrets | Already in use for DOPPLER_TOKEN |

## Current State

```
Doppler Project: b28-consult
├── dev_personal  (exists - local dev, personal token)
├── dev           (MISSING - needed for CI)
└── prd           (MISSING - needed for CI)
```

## Target State

```
Doppler Project: b28-consult
├── dev_personal  (local dev, personal token)
├── dev           (CI/CD deployments to dev environment)
└── prd           (CI/CD deployments to production)
```

## Implementation Steps

### 010-A: Create dev/prd configs in Doppler

1. Log into Doppler dashboard
2. Navigate to project `b28-consult`
3. Create `dev` environment/config:
   - Copy secrets from `dev_personal` as starting point
   - Ensure all required secrets present:
     - `CLOUDFLARE_API_TOKEN`
     - `CLOUDFLARE_ACCOUNT_ID`
     - `NEON_DATABASE_URL`
     - `INTAKE_API_KEY`
     - `SECRET_KEY`
     - Other Django/deployment secrets
4. Create `prd` environment/config:
   - Production-specific values
   - Separate database, different SECRET_KEY

### 010-B: Update GitHub DOPPLER_TOKEN

1. Create Service Account in Doppler with access to `dev` and `prd` configs
2. Generate Service Token for the service account
3. Update GitHub repository secret `DOPPLER_TOKEN` with new token
4. Verify token has correct scope: `doppler configs` should show `dev` and `prd`

### 010-C: Verify Deploy Sites workflow

1. Trigger `just sites-ci-trigger coffee-shop dev`
2. Verify workflow completes successfully
3. Confirm site is live at expected URL

## Related

- EP-005: Client Sites at Scale (completed, but CI deploy broken)
- `.github/workflows/deploy-sites.yml` - the workflow that needs this fix
- `.github/workflows/deploy.yml` - main deploy workflow (also uses Doppler)

## Progress Log

### 2026-01-22
- EP created after Deploy Sites workflow failed with Doppler access error
- Identified root cause: `dev_personal` config exists but `dev` config missing
- CI workflows hardcoded to expect `dev` and `prd` config names
