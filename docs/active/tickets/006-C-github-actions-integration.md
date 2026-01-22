# 006-C: GitHub Actions Integration

**EP:** [EP-006-automated-deploy-validation](../enhancement_proposals/EP-006-automated-deploy-validation.md)
**Status:** completed

## Summary

Integrate the Dagger pre-deploy pipeline with GitHub Actions so the same validation runs on every PR and before deployments.

## Acceptance Criteria

- [x] `.github/workflows/validate.yml` runs on PRs
- [x] Dagger pipeline runs identically in CI as locally
- [x] Secrets injected via GitHub Secrets → Doppler (single DOPPLER_TOKEN)
- [x] PR checks block merge if validation fails
- [x] Deploy workflow gates on pre-deploy success

## Implementation Notes

### Workflow: validate.yml

```yaml
name: Validate

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_call:  # Allow other workflows to call this

jobs:
  pre-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Dagger CLI
        uses: dagger/dagger-for-github@v6

      - name: Run pre-deploy validation
        run: cd dagger && dagger call pre-deploy --source=..

      - name: Upload validation report (JSON)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation-report.json
```

### Workflow: deploy.yml

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
      skip_validation:
        type: boolean
        default: false

jobs:
  validate:
    if: ${{ !inputs.skip_validation }}
    uses: ./.github/workflows/validate.yml

  deploy-worker:
    needs: [validate]
    if: always() && (needs.validate.result == 'success' || inputs.skip_validation)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dopplerhq/cli-action@v3
      - name: Deploy to Cloudflare
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          cd workers/intake
          pnpm install --frozen-lockfile
          doppler run -- pnpm wrangler deploy

  deploy-sites:
    needs: [validate]
    if: always() && (needs.validate.result == 'success' || inputs.skip_validation)
    runs-on: ubuntu-latest
    strategy:
      matrix:
        site: [coffee-shop]
    steps:
      - uses: actions/checkout@v4
      - uses: dopplerhq/cli-action@v3
      - name: Build and deploy site
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          pnpm install --frozen-lockfile
          cd sites/${{ matrix.site }}
          pnpm build
          doppler run -- pnpm wrangler pages deploy dist
```

### Secrets Configuration

GitHub Secrets needed:

| Secret | Source | Purpose |
|--------|--------|---------|
| `DOPPLER_TOKEN` | Doppler service token | Access all secrets via `doppler run` |

All deployment secrets flow through Doppler:
- `CLOUDFLARE_API_TOKEN` - Worker/Pages deployment
- `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account
- `NEON_DATABASE_URL` - Database connection
- `INTAKE_API_KEY` - Worker API key

### Branch Protection

Configure for `main`:

- [x] Require status checks: `pre-deploy`
- [x] Require branches to be up to date
- [x] Do not allow bypassing

## Progress

### 2026-01-21
- Created `.github/workflows/validate.yml`:
  - Runs Dagger pre-deploy validation on PRs and pushes to main
  - Uses `workflow_call` to allow other workflows to invoke it
  - Uploads JSON validation report as artifact
  - No secrets needed (Dagger uses self-contained test containers)
- Updated `.github/workflows/deploy.yml`:
  - Gates deployment on validate workflow success
  - Added `skip_validation` option for emergencies
  - Uses Doppler for all secrets (single `DOPPLER_TOKEN` in GitHub)
  - Deploys Worker to Cloudflare Workers via `doppler run`
  - Deploys Sites to Cloudflare Pages with matrix strategy
  - Added deployment summary step

### GitHub Secrets Required
Configure ONE secret in repository Settings → Secrets:
- `DOPPLER_TOKEN` - Doppler service token (all other secrets flow through Doppler)

To create a Doppler service token:
1. Go to https://dashboard.doppler.com
2. Select project: `consult`
3. Go to Access → Service Tokens → Generate
4. Name: `github_actions`, Config: `prd` (or environment-specific)
5. Copy the token (starts with `dp.st.`)

All deployment secrets (CLOUDFLARE_API_TOKEN, NEON_DATABASE_URL, etc.) are managed in Doppler.

**Ticket complete**
