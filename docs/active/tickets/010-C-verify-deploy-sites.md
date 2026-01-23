# 010-C: Verify Deploy Sites Workflow

**EP:** [EP-010-doppler-ci-config](../enhancement_proposals/EP-010-doppler-ci-config.md)
**Status:** pending

## Summary

Verify the Deploy Sites CI/CD workflow works end-to-end after Doppler configuration is fixed.

## Acceptance Criteria

- [ ] `just sites-ci-trigger coffee-shop dev` completes successfully
- [ ] Site deploys to Cloudflare Pages
- [ ] Deployment URL is accessible
- [ ] Workflow summary shows success

## Implementation Notes

```bash
# Trigger the workflow
just sites-ci-trigger coffee-shop dev

# Watch the workflow
just sites-ci-watch

# Check status
just sites-ci-status
```

Expected output:
```
completed success Deploy Sites ...
```

If successful, also verify:
1. `just sites-ci-trigger all dev` - deploys all sites
2. PR preview deploys work (create test PR)

## Progress

(Not started)
