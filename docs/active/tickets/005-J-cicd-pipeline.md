# 005-J: CI/CD Pipeline for Sites

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Set up GitHub Actions to automatically build and deploy sites on push.

## Acceptance Criteria

- [ ] Workflow triggers on push to main affecting `sites/**`
- [ ] Detects which sites changed
- [ ] Builds only changed sites
- [ ] Deploys to Cloudflare Pages via wrangler
- [ ] Uses Doppler for secrets
- [ ] Supports manual deploy of specific site
- [ ] Preview deploys for PRs

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

## Progress

(Not started)
