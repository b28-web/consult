# 006-C: GitHub Actions Integration

**EP:** [EP-006-automated-deploy-validation](../enhancement_proposals/EP-006-automated-deploy-validation.md)
**Status:** pending

## Summary

Integrate the Dagger pre-deploy pipeline with GitHub Actions so the same validation runs on every PR and before deployments.

## Acceptance Criteria

- [ ] `.github/workflows/validate.yml` runs on PRs
- [ ] Dagger pipeline runs identically in CI as locally
- [ ] Secrets injected via GitHub Secrets → Doppler
- [ ] PR checks block merge if validation fails
- [ ] Deploy workflow gates on pre-deploy success

## Implementation Notes

### Workflow: validate.yml

```yaml
name: Validate

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  pre-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Dagger
        uses: dagger/dagger-for-github@v6

      - name: Install Doppler
        uses: dopplerhq/cli-action@v3

      - name: Run pre-deploy validation
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run -- dagger call pre-deploy

      - name: Upload validation report
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
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  validate:
    uses: ./.github/workflows/validate.yml
    secrets: inherit

  deploy-worker:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Cloudflare
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: |
          cd workers/intake
          pnpm install
          pnpm wrangler deploy

  deploy-sites:
    needs: validate
    runs-on: ubuntu-latest
    strategy:
      matrix:
        site: [coffee-shop]
    steps:
      - uses: actions/checkout@v4
      - name: Build and deploy site
        run: |
          cd sites/${{ matrix.site }}
          pnpm install
          pnpm build
          pnpm wrangler pages deploy dist
```

### Secrets Configuration

GitHub Secrets needed:

| Secret | Source | Purpose |
|--------|--------|---------|
| `DOPPLER_TOKEN` | Doppler service token | Access all other secrets |
| `CLOUDFLARE_API_TOKEN` | Cloudflare | Worker/Pages deployment |

All other secrets (DATABASE_URL, etc.) flow through Doppler.

### Branch Protection

Configure for `main`:

- [x] Require status checks: `pre-deploy`
- [x] Require branches to be up to date
- [x] Do not allow bypassing

## Progress

(Updated as work proceeds)
