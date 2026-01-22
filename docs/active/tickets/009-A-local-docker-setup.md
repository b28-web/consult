# 009-A: Local Docker Setup

## Parent EP
[EP-009: Ansible Deployment](../enhancement_proposals/EP-009-ansible-deployment.md)

## Objective
Create Docker configuration for local development and e2e testing.

## Acceptance Criteria

- [x] `apps/web/Dockerfile` builds Django app
- [x] `docker-compose.yml` at repo root with services: django, postgres, redis
- [x] `just dev` starts the local stack
- [x] `just dev-down` stops and cleans up
- [x] Django can connect to Postgres and Redis
- [x] Hot reload works for code changes

## Technical Details

### Dockerfile (`apps/web/Dockerfile`)
```dockerfile
FROM python:3.12-slim
# Install uv, copy deps, run with gunicorn
```

### docker-compose.yml (repo root)
```yaml
services:
  django:
    build: ./apps/web
    ports: ["8000:8000"]
    volumes: ["./apps/web:/app"]  # hot reload
    depends_on: [postgres, redis]
  postgres:
    image: postgres:16
  redis:
    image: redis:7-alpine
```

### justfile commands
- `dev`: `docker compose up`
- `dev-down`: `docker compose down -v`
- `dev-shell`: `docker compose exec django bash`

## Out of Scope
- Production Docker deployment (using Ansible instead)
- Container registry setup

## Progress Log

### 2026-01-22
- Created `apps/web/Dockerfile` using Python 3.13-slim + uv
- Updated `docker-compose.yml` with django, postgres, redis services
- Added local postgres connection (no Neon dependency for local dev)
- Added justfile commands: `dev`, `dev-down`, `dev-shell`, `dev-manage`, `dev-migrate`
- Renamed old `dev` to `dev-native` for users who prefer Doppler+Neon
- Worker service moved to `--profile worker` (optional, for e2e tests)
- Tested: build, startup, migrations, healthcheck all pass
- Hot reload works via volume mount `./apps:/app/apps`
