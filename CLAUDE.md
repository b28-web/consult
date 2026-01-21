# CLAUDE.md - AI Assistant Context

This file provides context for AI coding assistants working on this codebase.

## Project Overview

**Consult** is a multi-tenant Django web agency platform. Each client gets:
- An Astro static site (marketing/frontpage)
- A Django-powered dashboard (inbox, CRM, scheduling)
- Access via a shared multi-tenant admin

The goal is fast delivery of business value with strong bus-factor resilience.

## Directory Structure

```
/
├── apps/
│   └── web/              # Django application (multi-tenant backend)
├── sites/                # Astro static sites (one subdirectory per client)
├── workers/              # Cloudflare Workers (intake endpoints, webhooks)
├── packages/             # Shared code/types across apps
├── scripts/              # Utility scripts for dev/deploy
├── .github/workflows/    # CI/CD pipelines
└── pyproject.toml        # Python project config (uv, ruff, mypy, pytest)
```

## Environment Setup

This project uses **Flox** for environment management and **Doppler** for secrets.

```bash
# Activate the development environment
flox activate

# Secrets are injected via Doppler - never hardcode or use .env files
doppler run -- <command>
```

## Key Conventions

### Python (Django)

- **Package manager**: uv (not pip, not poetry)
- **Formatter/Linter**: ruff (not black, not isort, not flake8)
- **Type checker**: mypy with strict mode
- **Testing**: pytest with pytest-django and factory_boy
- **All code must pass**: `ruff check`, `ruff format --check`, `mypy`, `pytest`

### Multi-Tenancy Pattern

All tenant-scoped models inherit from a base with `client` FK:

```python
class ClientScopedModel(models.Model):
    client = models.ForeignKey("core.Client", on_delete=models.CASCADE)

    class Meta:
        abstract = True
```

Always use `ClientScopedManager` for queries - never raw querysets that bypass tenant filtering.

### Code Style

- Prefer explicit over implicit
- No magic strings - use constants or enums
- Type hints on all function signatures
- Docstrings on public APIs only (not obvious methods)
- Tests are required for business logic

## What NOT To Do

### Environment & Tools

- **Never install packages globally** - use flox/uv
- **Never create .env files** - secrets come from Doppler
- **Never use workaround tools** (jq, timeout, etc.) if the proper tool isn't available - fix the environment instead
- **Never hardcode secrets, API keys, or credentials**

### Code Changes

- **Never modify ClientScopedManager** without discussing the security implications
- **Never bypass tenant isolation** in queries
- **Never skip type hints** on new code
- **Never commit code that fails ruff/mypy/pytest**

### Git

- **Never force push to main**
- **Never commit large files** (images, binaries) - use appropriate storage

> **Note (Rapid Build Phase)**: During solo development, committing directly to main is acceptable. Switch to feature branches when collaborating.

## Common Workflows

### Running the Django dev server

```bash
flox activate
doppler run -- uv run python apps/web/manage.py runserver
```

### Running tests

```bash
flox activate
doppler run -- uv run pytest
```

### Running quality checks

```bash
# All checks (what CI runs)
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest

# Auto-fix formatting
uv run ruff format .
uv run ruff check --fix .
```

### Adding a Python dependency

```bash
uv add <package>           # Runtime dependency
uv add --dev <package>     # Dev dependency
```

### Database migrations

```bash
doppler run -- uv run python apps/web/manage.py makemigrations
doppler run -- uv run python apps/web/manage.py migrate
```

## Architecture Decisions

See `ARCHITECTURE.md` for detailed system design documentation.

Key patterns:
- **Submission Queue**: All inbound messages (form, SMS, voicemail) go through a `Submission` table before processing
- **AI Classification**: Messages are classified using BAML schemas
- **Channel Agnostic**: The inbox abstracts over email, SMS, voicemail - same interface for staff

## Testing Guidelines

- Unit tests for business logic
- Integration tests for API endpoints
- Factory classes for test data (never fixtures)
- Test multi-tenancy: user A cannot see user B's data

## Getting Help

- Check `ARCHITECTURE.md` for system design questions
- Check `pyproject.toml` for available scripts and dependencies
- Check `.github/workflows/` for CI configuration
