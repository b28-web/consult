# 001-B: Intake Worker Deployment

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** in-progress

## Summary

Deploy the intake worker to Cloudflare Workers with Neon database writes working.

## Acceptance Criteria

- [x] @neondatabase/serverless added to worker
- [x] `writeSubmission()` actually inserts to database (code complete)
- [ ] Worker deploys via `doppler run -- wrangler deploy`
- [ ] Form POST to `/intake/{client}/form` creates submission row
- [ ] Health endpoint returns 200

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
- **Pending**: Actual deployment requires Doppler secrets and Neon database to be configured (see EP-001 dependencies)
