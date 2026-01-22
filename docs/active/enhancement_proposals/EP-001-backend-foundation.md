# EP-001: Backend Foundation

**Status:** completed
**Sprint:** 2026-01-21 to 2026-01-22
**Last Updated:** 2026-01-22

## Goal

Establish the core backend infrastructure: Django running with migrations, intake worker deployed, first client site live. This sprint proves the full stack works end-to-end.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 001-A | Django backend bootstrap | completed |
| 001-B | Intake worker deployment | completed |
| 001-C | First client site (coffee-shop) | completed |

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
- [x] Doppler project configured with secrets
- [x] Neon database created

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

### 2026-01-21 (session 4)
- **001-C scaffolded**: Coffee-shop site created and building
  - Copied template to sites/coffee-shop/
  - Configured "The Daily Grind" branding (4 services)
  - DaisyUI theme with warm brown (#78350f) / cream (#fef3c7)
  - Site builds successfully with pnpm
- **Template fixes applied**:
  - Changed Astro output from deprecated "hybrid" to "static"
  - Added @consult/shared-ui workspace dependency
- **Blocked**: Both 001-B and 001-C deployment blocked on Doppler/Neon setup
- Next: Configure Doppler and Neon to unblock deployments

### 2026-01-22 (session 5)
- **Doppler + Neon configured**:
  - Created interactive `just setup-infra` wizard
  - Added docs/knowledge/patterns/neon-doppler-setup.md
  - Configured all required secrets via Doppler service token
- **001-B completed**: Intake worker fully working
  - Fixed NOT NULL constraint on `error` column
  - Fixed ReadableStream locked bug in honeypot check
  - Worker runs in `--remote` mode (Cloudflare edge)
- **001-C completed**: Form submission verified end-to-end
  - Site → Worker → Neon database flow working
- **Test infrastructure created**:
  - `just test-local` runs Django + Worker + E2E tests
  - Fixed Cloudflare bot detection (User-Agent header)
  - All smoke tests and intake tests pass
- **Production deployment deferred to EP-007** (Pulumi infrastructure)

## Retrospective

**What went well:**
- Django bootstrap was smooth (good starter template)
- Neon serverless driver worked well with Cloudflare Workers
- Interactive setup wizard saved time configuring secrets

**What was tricky:**
- workerd TLS issues with Neon required `--remote` mode workaround
- Cloudflare bot detection blocked Python test requests
- Database schema had NOT NULL constraint mismatch with worker INSERT

**Key learnings:**
- Always test with production-like infrastructure (Neon, not local Postgres)
- Cloudflare Workers need careful User-Agent handling in tests
- `--remote` mode is more reliable than `--local` for external DB connections
