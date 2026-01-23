# 010-A: Create dev/prd configs in Doppler

**EP:** [EP-010-doppler-ci-config](../enhancement_proposals/EP-010-doppler-ci-config.md)
**Status:** complete

## Summary

Create `dev` and `prd` environment configs in Doppler project `b28-consult` to enable CI/CD workflows.

## Acceptance Criteria

- [x] `dev` config exists in Doppler with all required secrets
- [ ] `prd` config exists in Doppler with production values (deferred)
- [x] Both configs have: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, NEON_DATABASE_URL, INTAKE_API_KEY, SECRET_KEY

## Implementation Notes

This is a manual task in Doppler dashboard:

1. Go to https://dashboard.doppler.com
2. Select project `b28-consult`
3. Create new environment `dev`:
   - Base it on `dev_personal`
   - Verify all secrets are present
4. Create new environment `prd`:
   - Use production-specific values
   - Different SECRET_KEY, DATABASE_URL pointing to prod

Required secrets checklist:
- `CLOUDFLARE_API_TOKEN` - CF API token with Pages deploy permission
- `CLOUDFLARE_ACCOUNT_ID` - CF account ID
- `NEON_DATABASE_URL` - Postgres connection string
- `INTAKE_API_KEY` - API key for intake worker
- `SECRET_KEY` - Django secret key
- `SSH_PRIVATE_KEY` - For Ansible deployment (if applicable)

## Progress

### 2026-01-22
- Created `dev` config in Doppler dashboard
- Copied all secrets from `dev_personal` to `dev`
- `prd` config deferred (not needed for initial CI verification)
