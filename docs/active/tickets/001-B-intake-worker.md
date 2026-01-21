# 001-B: Intake Worker Deployment

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** pending

## Summary

Deploy the intake worker to Cloudflare Workers with Neon database writes working.

## Acceptance Criteria

- [ ] @neondatabase/serverless added to worker
- [ ] `writeSubmission()` actually inserts to database
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

(Not started)
