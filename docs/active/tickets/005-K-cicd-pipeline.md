# 005-K: CI/CD Pipeline for Sites

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete

## Summary

Set up GitHub Actions to automatically build and deploy sites on push.

## Acceptance Criteria

- [x] Workflow triggers on push to main affecting `sites/**`
- [x] Detects which sites changed
- [x] Builds only changed sites
- [x] Deploys to Cloudflare Pages via wrangler
- [x] Uses Doppler for secrets
- [x] Supports manual deploy of specific site
- [x] Preview deploys for PRs

## Implementation Notes

```yaml
# .github/workflows/deploy-sites.yml
name: Deploy Sites

on:
  push:
    branches: [main]
    paths:
      - 'sites/**'
  workflow_dispatch:
    inputs:
      site:
        description: 'Site to deploy (or "all")'
        required: true
        default: 'all'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      sites: ${{ steps.changes.outputs.sites }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: changes
        run: |
          # Detect changed sites
          SITES=$(git diff --name-only HEAD~1 | grep '^sites/' | cut -d'/' -f2 | sort -u | jq -R -s -c 'split("\n") | map(select(. != ""))')
          echo "sites=$SITES" >> $GITHUB_OUTPUT

  deploy:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        site: ${{ fromJson(needs.detect-changes.outputs.sites) }}
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'pnpm'
      - run: pnpm install
      - name: Build
        run: pnpm --filter "./sites/${{ matrix.site }}" build
      - name: Deploy
        uses: cloudflare/wrangler-action@v3
        with:
          workingDirectory: sites/${{ matrix.site }}
          command: pages deploy dist --project-name=consult-${{ matrix.site }}
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

Doppler integration for runtime secrets:
- Build-time: Not needed (static sites)
- Runtime secrets: Injected via Cloudflare env vars or Doppler integration

## Monitoring Commands

Added to justfile for CI/CD monitoring:

```bash
just ci-status              # Show recent workflow runs
just ci-watch RUN_ID        # Watch a running workflow
just ci-logs RUN_ID         # Show logs for a workflow
just ci-logs-failed RUN_ID  # Show failed job logs
just sites-ci-status        # Check Deploy Sites workflow runs
just sites-ci-trigger SITE ENV  # Manually trigger deploy
just sites-ci-watch         # Watch latest Deploy Sites run
```

## Known Issues

**Blocked by EP-010:** Workflow is complete but fails because Doppler config `dev` doesn't exist (only `dev_personal`). See [EP-010-doppler-ci-config](../enhancement_proposals/EP-010-doppler-ci-config.md).

## Progress

### 2026-01-22
- Created `.github/workflows/deploy-sites.yml`
- Implemented change detection using git diff
- Matrix build deploys only changed sites in parallel
- Cloudflare Pages deployment via wrangler with Doppler secrets
- Manual trigger (`workflow_dispatch`) with site selector and environment choice
- PR preview deploys with branch naming `pr-{number}`
- PR comments with preview URLs (updates existing comment or creates new)
- Deployment summary in GitHub Actions UI
- Excludes `_template/`, `registry.yaml`, and `.gitkeep` from triggering builds
- Added CI/CD monitoring commands to justfile
- Fixed pnpm version mismatch (removed hardcoded v9, reads from package.json)
- Fixed error handling to show deploy errors
- **Blocked:** Doppler token lacks access to `dev` config (tracked in EP-010)
