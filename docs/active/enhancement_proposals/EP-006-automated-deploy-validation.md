# EP-006: Automated Deploy Validation

**Status:** completed
**Sprint:** 2026-01-21 to 2026-01-28
**Last Updated:** 2026-01-21

## Goal

Create a fully automated, agent-driven test pipeline that validates the entire stack before deployment. An LLM agent should be able to run a single command to verify that a deploy would succeed, catching issues before they hit production.

## Problem

Currently, testing requires:
- Manual Docker Compose orchestration
- Multiple commands to verify different components
- No unified "pre-flight check" for deployments
- CI/CD pipeline gaps between local dev and production

## Solution

Use **Dagger** to create a programmable CI/CD pipeline that:
1. Runs entirely in containers (reproducible, no host pollution)
2. Provides a single entry point for full validation
3. Can be run locally or in CI with identical behavior
4. Outputs clear pass/fail results for LLM agents

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 006-A | Dagger pipeline setup | completed |
| 006-B | Pre-deploy validation flow | completed |
| 006-C | GitHub Actions integration | completed |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pipeline tool | Dagger | Containers as code, same local/CI behavior, Python SDK |
| Test database | Postgres container | Fully isolated, no external deps, reproducible |
| Intake E2E | External (just test-local) | Worker uses Neon HTTP API, can't use generic Postgres |
| Secret injection | Doppler → Dagger | Single source of truth for secrets |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     just pre-deploy                              │
│                           │                                      │
│                     ┌─────▼─────┐                                │
│                     │  Dagger   │                                │
│                     │  Pipeline │                                │
│                     └─────┬─────┘                                │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                    │
│         ▼                 ▼                 ▼                    │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│   │  Build   │     │  Test    │     │  Verify  │                │
│   │  Stage   │     │  Stage   │     │  Stage   │                │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘                │
│        │                │                │                       │
│   ┌────▼────┐      ┌────▼────┐     ┌────▼────┐                  │
│   │ Django  │      │ Smoke   │     │ Intake  │                  │
│   │ Container│     │ Tests   │     │ E2E     │                  │
│   ├─────────┤      ├─────────┤     ├─────────┤                  │
│   │ Worker  │      │ Django  │     │ Form    │                  │
│   │ Container│     │ Check   │     │ Submit  │                  │
│   ├─────────┤      ├─────────┤     ├─────────┤                  │
│   │ Site    │      │ Mypy    │     │ DB      │                  │
│   │ Build   │      │ Ruff    │     │ Verify  │                  │
│   └─────────┘      └─────────┘     └─────────┘                  │
│                                                                  │
│   Output: JSON report + exit code                                │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Interface

The pipeline is designed for LLM agents:

```bash
# Single command validation
just pre-deploy

# Expected output (success):
# ══════════════════════════════════════
# PRE-DEPLOY VALIDATION: PASSED
# ══════════════════════════════════════
# ✓ Build: Django container
# ✓ Build: Worker container
# ✓ Build: coffee-shop site
# ✓ Quality: ruff check
# ✓ Quality: mypy
# ✓ Test: pytest (12 passed)
# ✓ Integration: smoke tests
# ✓ Integration: intake e2e
#
# Ready to deploy!
# Exit code: 0

# Expected output (failure):
# ══════════════════════════════════════
# PRE-DEPLOY VALIDATION: FAILED
# ══════════════════════════════════════
# ✓ Build: Django container
# ✗ Build: Worker container
#   → TypeScript error in src/index.ts:45
# ...
# Exit code: 1
```

## Success Criteria

- [x] `just pre-deploy` runs full validation in < 5 minutes (~15s cached)
- [x] Same command works locally and in GitHub Actions
- [x] Clear, parseable output for LLM agents
- [x] Catches: build failures, type errors, test failures, integration issues
- [x] No host system pollution (everything in containers)

## Dependencies

- [x] Docker Compose setup (from current work)
- [x] Test scripts (`scripts/test_intake.py`)
- [x] Dagger CLI and Python SDK
- [x] GitHub Actions workflow

## Progress Log

### 2026-01-21
- EP created
- Docker Compose foundation in place
- Test scripts ready for integration

### 2026-01-21 (later)
- **006-A completed**: Dagger pipeline setup working
  - Dagger CLI in Flox environment
  - `dagger/src/consult_pipeline/main.py` with all pipeline functions
  - `just pre-deploy` command integrated
- **006-B in progress**: Fixing deferred items
  - Fixed site build (node:22, pnpm-lock sync)
  - Fixed pytest (PYTHONPATH for apps import)
  - All 6 validation stages passing:
    - ✓ Build: Django, Worker, coffee-shop site
    - ✓ Quality: ruff, mypy, pytest
  - Remaining: parallel execution, integration tests, JSON output

### 2026-01-21 (integration tests)
- **006-B continued**: Added Stage 3 integration tests
  - Postgres service container (postgres:16-alpine) for isolated test DB
  - Django integration container with service binding
  - 4 integration checks implemented:
    - Run migrations (apply to test DB)
    - Django health (GET /admin/login/)
    - Migration check (manage.py migrate --check)
    - Worker health (GET /health, local mode)
  - Added `just pre-deploy-integration` for standalone testing
  - Design decision: Intake E2E requires Neon HTTP API, stays in `just test-local`
  - Remaining: parallel execution, JSON output

### 2026-01-21 (final)
- **006-B completed**: All remaining items done
  - Parallel execution: Build and quality stages now run with `asyncio.gather()`
  - JSON output: Added `--json-output` flag to all pipeline functions
  - Added `just pre-deploy-json` command for machine-readable output
  - All acceptance criteria met

### 2026-01-21 (EP complete)
- **006-C completed**: GitHub Actions integration
  - Created `.github/workflows/validate.yml` - runs Dagger pipeline on PRs
  - Updated `.github/workflows/deploy.yml` - gates on validation, deploys Worker + Sites
  - All EP-006 tickets complete
  - **EP-006 COMPLETE** - Ready for archive

## References

- [Dagger Documentation](https://docs.dagger.io)
- [Dagger Python SDK](https://docs.dagger.io/sdk/python)
- [Doppler + Dagger Integration](https://docs.doppler.com/docs/dagger)
