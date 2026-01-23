# 010-B: Update GitHub DOPPLER_TOKEN

**EP:** [EP-010-doppler-ci-config](../enhancement_proposals/EP-010-doppler-ci-config.md)
**Status:** pending

## Summary

Create a Doppler Service Account token with access to `dev` and `prd` configs, and update GitHub Actions secrets.

## Acceptance Criteria

- [ ] Service Account exists in Doppler with access to dev/prd configs
- [ ] Service Token generated for CI/CD use
- [ ] GitHub secret `DOPPLER_TOKEN` updated with new token
- [ ] Token verified: `doppler configs` shows both `dev` and `prd`

## Implementation Notes

### In Doppler Dashboard

1. Go to project `b28-consult` > Access
2. Create Service Account (e.g., "GitHub Actions CI")
3. Grant access to `dev` and `prd` configs
4. Generate Service Token

### In GitHub

1. Go to repository Settings > Secrets and variables > Actions
2. Update `DOPPLER_TOKEN` with the new service token
3. The token format should be `dp.st.xxx...`

### Verification

```bash
# With the new token, this should work:
DOPPLER_TOKEN=dp.st.xxx doppler configs
# Should show both dev and prd
```

## Progress

(Not started)
