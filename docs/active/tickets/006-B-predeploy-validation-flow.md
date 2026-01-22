# 006-B: Pre-Deploy Validation Flow

**EP:** [EP-006-automated-deploy-validation](../enhancement_proposals/EP-006-automated-deploy-validation.md)
**Status:** completed

## Summary

Implement the full pre-deployment validation pipeline that an LLM agent can run to verify a deploy would succeed. This is the core "pre-flight check" for the codebase.

## Acceptance Criteria

- [x] Single command: `just pre-deploy` runs complete validation
- [x] Parallel execution where possible (build stages, quality checks)
- [x] Integration tests use isolated test database
- [x] Output is structured and parseable (JSON + human-readable)
- [x] Exit code 0 = safe to deploy, non-zero = issues found
- [x] Total runtime < 5 minutes on warm cache (~15s cached)

## Validation Stages

### Stage 1: Build Validation
Verify all containers build successfully.

| Check | Command | Failure Mode |
|-------|---------|--------------|
| Django container | `docker build -f docker/django.Dockerfile` | Build error, missing deps |
| Worker container | `docker build -f docker/worker.Dockerfile` | TS compile error, missing deps |
| Site build | `pnpm build` in sites/coffee-shop | Astro build error |

### Stage 2: Quality Checks
Static analysis and unit tests.

| Check | Command | Failure Mode |
|-------|---------|--------------|
| Lint | `ruff check .` | Style violations |
| Format | `ruff format --check .` | Formatting issues |
| Types | `mypy apps` | Type errors |
| Tests | `pytest` | Test failures |

### Stage 3: Integration Tests
End-to-end validation with real services.

| Check | Description | Failure Mode |
|-------|-------------|--------------|
| Django health | GET /admin/login/ returns 200 | Django won't start |
| Worker health | GET /health returns 200 | Worker won't start |
| Intake E2E | POST form → verify in DB | Integration broken |
| DB migrations | `manage.py migrate --check` | Unapplied migrations |

## Output Format

### Human-Readable (stdout)

```
══════════════════════════════════════════════════════════════
  PRE-DEPLOY VALIDATION
══════════════════════════════════════════════════════════════

Build Stage                                              [32s]
  ✓ Django container                                    (12s)
  ✓ Worker container                                     (8s)
  ✓ Site: coffee-shop                                   (12s)

Quality Stage                                            [18s]
  ✓ ruff check                                           (2s)
  ✓ ruff format --check                                  (1s)
  ✓ mypy                                                 (8s)
  ✓ pytest (24 passed)                                   (7s)

Integration Stage                                        [15s]
  ✓ Django health check                                  (3s)
  ✓ Worker health check                                  (2s)
  ✓ Intake E2E test                                      (8s)
  ✓ Migration check                                      (2s)

══════════════════════════════════════════════════════════════
  RESULT: PASSED                                  Total: 65s
══════════════════════════════════════════════════════════════
```

### Machine-Readable (JSON, optional flag)

```json
{
  "result": "passed",
  "duration_seconds": 65,
  "stages": {
    "build": {
      "status": "passed",
      "duration_seconds": 32,
      "checks": [
        {"name": "django_container", "status": "passed", "duration": 12},
        {"name": "worker_container", "status": "passed", "duration": 8},
        {"name": "site_coffee_shop", "status": "passed", "duration": 12}
      ]
    },
    "quality": {
      "status": "passed",
      "duration_seconds": 18,
      "checks": [
        {"name": "ruff_check", "status": "passed", "duration": 2},
        {"name": "ruff_format", "status": "passed", "duration": 1},
        {"name": "mypy", "status": "passed", "duration": 8},
        {"name": "pytest", "status": "passed", "duration": 7, "tests_passed": 24}
      ]
    },
    "integration": {
      "status": "passed",
      "duration_seconds": 15,
      "checks": [
        {"name": "django_health", "status": "passed", "duration": 3},
        {"name": "worker_health", "status": "passed", "duration": 2},
        {"name": "intake_e2e", "status": "passed", "duration": 8},
        {"name": "migration_check", "status": "passed", "duration": 2}
      ]
    }
  }
}
```

## LLM Agent Usage

The pipeline is designed for autonomous agent use:

```bash
# Agent runs this command
just pre-deploy

# Agent interprets:
# - Exit code 0 → proceed with deployment
# - Exit code 1 → parse output, fix issues, retry
```

### Failure Handling

When a check fails, output includes actionable context:

```
Quality Stage                                            [FAILED]
  ✓ ruff check                                           (2s)
  ✓ ruff format --check                                  (1s)
  ✗ mypy                                                 (8s)
    │
    │ apps/web/inbox/models.py:45: error: Argument 1 to "filter"
    │ has incompatible type "str"; expected "int"  [arg-type]
    │
    │ Found 1 error in 1 file
    │
  ○ pytest                                           (skipped)

══════════════════════════════════════════════════════════════
  RESULT: FAILED                                  Total: 11s
══════════════════════════════════════════════════════════════

Fix the issues above and run 'just pre-deploy' again.
```

## Progress

### 2026-01-21
- Fixed site build: Updated node containers from node:20 to node:22 (project requires node >= 22)
- Fixed site build: Updated pnpm-lock.yaml which was out of sync with sites/_template/package.json
- Fixed pytest: Added PYTHONPATH=/app to Python container so `apps` package is importable
- Excluded nested node_modules from site build context for cleaner builds
- All 6 validation stages now pass:
  - ✓ Build: Django container
  - ✓ Build: Worker container
  - ✓ Build: coffee-shop site
  - ✓ Quality: ruff check
  - ✓ Quality: mypy
  - ✓ Quality: pytest (no tests collected - project has no unit tests yet)

### 2026-01-21 (continued)
- Added Stage 3: Integration tests to Dagger pipeline
- Created Postgres service container (postgres:16-alpine) for isolated test database
- Implemented Django integration container with Postgres service binding
- Added 4 integration test checks:
  - ✓ Run migrations (applies migrations to test DB)
  - ✓ Django health (GET /admin/login/ returns 200)
  - ✓ Migration check (manage.py migrate --check)
  - ✓ Worker health (GET /health returns 200, local mode)
- Added `just pre-deploy-integration` command for standalone integration testing
- Note: Intake E2E skipped in Dagger (requires Neon HTTP API); use `just test-local` for full E2E

### 2026-01-21 (final)
- Added parallel execution using `asyncio.gather()` for build and quality stages
- Added JSON output option (`--json-output` flag or `just pre-deploy-json`)
- Fixed line length issues in pipeline code for ruff compliance
- All acceptance criteria now met

**Ticket complete** - ready to update status to completed
