# 006-A: Dagger Pipeline Setup

**EP:** [EP-006-automated-deploy-validation](../enhancement_proposals/EP-006-automated-deploy-validation.md)
**Status:** pending

## Summary

Set up Dagger with Python SDK to replace Docker Compose for automated testing. Create the foundational pipeline that builds all containers and runs basic validation.

## Acceptance Criteria

- [ ] Dagger CLI added to Flox environment
- [ ] Dagger Python SDK added to dev dependencies
- [ ] `dagger/` directory with pipeline code
- [ ] `just pre-deploy` command runs the Dagger pipeline
- [ ] Pipeline builds: Django, Worker, Site containers
- [ ] Pipeline runs: ruff, mypy, pytest
- [ ] Clear pass/fail output with timing

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

(Updated as work proceeds)
