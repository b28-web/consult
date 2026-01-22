# 006-A: Dagger Pipeline Setup

**EP:** [EP-006-automated-deploy-validation](../enhancement_proposals/EP-006-automated-deploy-validation.md)
**Status:** completed

## Summary

Set up Dagger with Python SDK to replace Docker Compose for automated testing. Create the foundational pipeline that builds all containers and runs basic validation.

## Acceptance Criteria

- [x] Dagger CLI added to Flox environment
- [x] Dagger Python SDK added to dev dependencies
- [x] `dagger/` directory with pipeline code
- [x] `just pre-deploy` command runs the Dagger pipeline
- [x] Pipeline builds: Django, Worker containers (Site deferred)
- [x] Pipeline runs: ruff, mypy (pytest deferred)
- [x] Clear pass/fail output with timing

## Implementation Notes

### Directory Structure

```
dagger/
├── src/
│   └── consult_pipeline/
│       ├── __init__.py
│       ├── main.py          # Entry point
│       ├── build.py         # Container build stages
│       ├── quality.py       # Linting, typing, tests
│       └── integration.py   # E2E tests
└── pyproject.toml           # Dagger module config
```

### Pipeline Stages

```python
@function
async def pre_deploy(self) -> str:
    """Full pre-deployment validation."""
    results = []

    # Stage 1: Build
    results.append(await self.build_django())
    results.append(await self.build_worker())
    results.append(await self.build_site("coffee-shop"))

    # Stage 2: Quality
    results.append(await self.run_ruff())
    results.append(await self.run_mypy())
    results.append(await self.run_pytest())

    # Stage 3: Integration
    results.append(await self.smoke_test())
    results.append(await self.intake_e2e())

    return format_report(results)
```

### Justfile Integration

```just
# Run pre-deploy validation via Dagger
pre-deploy:
    dagger call pre-deploy

# Run specific stage
pre-deploy-build:
    dagger call build-all

pre-deploy-quality:
    dagger call quality-all
```

### Secret Handling

Secrets flow from Doppler → Dagger:

```python
@function
async def with_secrets(self, container: dagger.Container) -> dagger.Container:
    """Inject secrets from Doppler into container."""
    return (
        container
        .with_secret_variable("DATABASE_URL", self.database_url)
        .with_secret_variable("SECRET_KEY", self.secret_key)
        # ... etc
    )
```

## Technical Notes

- Dagger runs its own Docker engine (BuildKit)
- Containers are cached aggressively - rebuilds are fast
- Pipeline code is type-checked and testable
- Can run locally or in CI with identical behavior

## Progress

### 2026-01-21
- Added `dagger` CLI to Flox environment (`.flox/env/manifest.toml`)
- Added `dagger-io>=0.15` to pyproject.toml dev dependencies
- Created `dagger/` directory with pipeline module:
  - `dagger/dagger.json` - Module configuration
  - `dagger/src/consult_pipeline/main.py` - Entry point with all pipeline functions
- Added justfile commands:
  - `just pre-deploy` - Full validation
  - `just pre-deploy-build` - Build only
  - `just pre-deploy-quality` - Quality only
  - Individual commands: `dagger-lint`, `dagger-typecheck`, `dagger-test`
- Formatted output with clear pass/fail status for LLM agents

**Working stages:**
- ✓ Django container build
- ✓ Worker container build
- ✓ ruff check (lint + format)
- ✓ mypy (type checking)

**Needs follow-up (deferred to 006-B):**
- Site build (pnpm workspace issues in containerized context)
- pytest (exit code handling for no-tests-collected case)

**Also fixed:**
- Fixed DJANGO_SETTINGS_MODULE in `.flox/env/manifest.toml`
- Added missing `apps/web/__init__.py`
- Added RUF012 ignore for migrations in pyproject.toml
- Fixed lint issues in `packages/schemas/`

### 2026-01-21 (completion)
- Ticket marked **completed**
- Deferred items (site build, pytest) addressed in 006-B
