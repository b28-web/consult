# EP-006: Automated Deploy Validation

**Status:** active
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
| 006-A | Dagger pipeline setup | pending |
| 006-B | Pre-deploy validation flow | pending |
| 006-C | GitHub Actions integration | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pipeline tool | Dagger | Containers as code, same local/CI behavior, Python SDK |
| Test database | Neon branch or ephemeral | Isolated test data, no prod pollution |
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

- [ ] `just pre-deploy` runs full validation in < 5 minutes
- [ ] Same command works locally and in GitHub Actions
- [ ] Clear, parseable output for LLM agents
- [ ] Catches: build failures, type errors, test failures, integration issues
- [ ] No host system pollution (everything in containers)

## Dependencies

- [x] Docker Compose setup (from current work)
- [x] Test scripts (`scripts/test_intake.py`)
- [ ] Dagger CLI and Python SDK
- [ ] GitHub Actions workflow

## Progress Log

### 2026-01-21
- EP created
- Docker Compose foundation in place
- Test scripts ready for integration

## References

- [Dagger Documentation](https://docs.dagger.io)
- [Dagger Python SDK](https://docs.dagger.io/sdk/python)
- [Doppler + Dagger Integration](https://docs.doppler.com/docs/dagger)
