# EP-001: Backend Foundation

**Status:** active
**Sprint:** 2026-01-21 to 2026-01-28
**Last Updated:** 2026-01-21

## Goal

Establish the core backend infrastructure: Django running with migrations, intake worker deployed, first client site live. This sprint proves the full stack works end-to-end.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 001-A | Django backend bootstrap | completed |
| 001-B | Intake worker deployment | in-progress |
| 001-C | First client site (coffee-shop) | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Neon Postgres | Serverless, branching, familiar |
| Secrets | Doppler | Centralized, env-aware |
| Sites runtime | Cloudflare Pages | Hybrid SSR, global edge |
| Worker runtime | Cloudflare Workers | Same platform, consistent |

## Dependencies

- [x] Project structure scaffolded
- [x] Models stubbed
- [ ] Doppler project configured with secrets
- [ ] Neon database created

## Progress Log

### 2026-01-21
- Sprint created
- All Django apps stubbed (core, inbox, crm)
- Worker intake code written
- Site template with DaisyUI ready
- Next: uncomment Django deps, run migrations

### 2026-01-21 (session 2)
- **001-A completed**: Django backend fully bootstrapped
  - Dependencies wired, settings use django-environ
  - All admin registrations created
  - Initial migrations generated
  - All quality checks pass (ruff, mypy)
- Next: Configure Doppler secrets, then 001-B (intake worker)

### 2026-01-21 (session 3)
- **001-B code complete**: Intake worker implementation done
  - Added @neondatabase/serverless dependency
  - Implemented writeSubmission() with actual Neon SQL INSERT
  - TypeScript compiles, wrangler builds successfully
- **Blocked**: Deployment requires Doppler project + Neon database setup
- Next: Configure Doppler secrets and Neon database, then deploy

## Retrospective

(Fill in when sprint completes)
