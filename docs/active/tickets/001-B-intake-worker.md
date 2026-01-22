# 001-B: Intake Worker Deployment

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** completed

## Summary

Deploy the intake worker to Cloudflare Workers with Neon database writes working.

## Acceptance Criteria

- [x] @neondatabase/serverless added to worker
- [x] `writeSubmission()` actually inserts to database
- [x] Worker runs via `wrangler dev --remote` (prod deployment pending EP-007)
- [x] Form POST to `/intake/{client}/form` creates submission row
- [x] Health endpoint returns 200

## Implementation Notes

```
workers/intake/package.json       # Add @neondatabase/serverless
workers/intake/src/index.ts       # Implement writeSubmission()
```

Neon serverless driver usage:
```typescript
import { neon } from "@neondatabase/serverless";

const sql = neon(env.NEON_DATABASE_URL);
await sql`INSERT INTO inbox_submission ...`;
```

## Progress

### 2026-01-21
- Added `@neondatabase/serverless` dependency to worker package.json
- Implemented `writeSubmission()` with actual Neon SQL INSERT
- TypeScript compiles successfully, wrangler dry-run builds (200KB / 52KB gzipped)

### 2026-01-22
- Configured Doppler secrets (NEON_DATABASE_URL, INTAKE_API_KEY)
- Fixed database INSERT to include `error` field (NOT NULL constraint)
- Fixed ReadableStream locked bug in honeypot check
- Created `just test-local` for end-to-end integration testing
- All tests pass: health endpoint, form submission, database verification
- Worker runs successfully in `--remote` mode (uses Cloudflare edge)
- **Note**: Production deployment to Cloudflare Workers deferred to EP-007
