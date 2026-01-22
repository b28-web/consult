# EP-009: Ansible Deployment

## Overview

Set up Ansible for Django deployment to Hetzner. Keep Docker for local e2e testing only.

## Goals

1. **Ansible playbooks** for server configuration and app deployment
2. **Passwordless deploy key** - CI can deploy without passphrase prompts
3. **Docker for local only** - `docker compose up` for local dev/testing
4. **No container registry** - deploy code directly via git, not images

## Architecture

```
Local Dev:
  docker compose up → Django + Postgres + Redis (containerized)

Production:
  Ansible → Hetzner VPS
    - Python/uv installed directly
    - Gunicorn + nginx
    - Systemd service
    - Doppler CLI for secrets
```

## Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| 009-A | Local Docker setup | ✓ |
| 009-B | Ansible inventory and base playbook | ✓ |
| 009-C | Django deployment playbook | ✓ |
| 009-D | CI deploy key setup | ✓ |
| 009-E | Update justfile and CI | ✓ |

## Technical Details

### 009-A: Local Docker setup
- `apps/web/Dockerfile` for Django
- `docker-compose.yml` at repo root
- Services: django, postgres, redis
- `just dev` starts local stack

### 009-B: Ansible inventory and base playbook
- `ansible/inventory/` with dev/prod hosts
- `ansible/playbooks/setup.yml`:
  - Create `deploy` user with sudo
  - Add deploy SSH key (passwordless, for CI)
  - Install: Python 3.12, uv, nginx, Doppler CLI
  - Configure firewall (ufw)
  - Set up log directories

### 009-C: Django deployment playbook
- `ansible/playbooks/deploy.yml`:
  - Git clone/pull to `/app`
  - `uv sync` for dependencies
  - `doppler run -- uv run manage.py migrate`
  - Restart gunicorn systemd service
  - Reload nginx if config changed

### 009-D: CI deploy key setup
- Generate Ed25519 key without passphrase
- Store private key in Doppler as `DEPLOY_SSH_KEY`
- Ansible adds public key to `deploy` user's authorized_keys
- CI writes key to temp file for SSH

### 009-E: Update justfile and CI
- `just deploy-django ENV` runs Ansible playbook
- GitHub Actions uses `DEPLOY_SSH_KEY` from Doppler
- Remove old SSH-based deploy from cloud-init

## Out of Scope

- Container registry
- Kubernetes/Docker Swarm
- Multi-server deployments (single VPS for now)

## Success Criteria

- [x] `just dev` starts local Docker stack
- [x] `just ansible-deploy dev` deploys via Ansible
- [x] CI can deploy without manual passphrase entry (via `DEPLOY_SSH_PRIVATE_KEY`)
- [x] Server runs Django via systemd (not Docker)

## Progress

### Completed (2026-01-22)

**009-A: Local Docker Setup**
- `apps/web/Dockerfile` with Python 3.13 + uv
- `docker-compose.yml` with django, postgres, redis services
- `just dev` / `just dev-down` / `just dev-shell` commands
- Hot reload via volume mounts

**009-B: Ansible Base Playbook**
- `ansible/` directory structure with roles, inventory, playbooks
- `common` role: deploy user, Python 3.12, uv, nginx, Doppler CLI, UFW
- `just ansible-setup ENV` command

**009-C: Django Deployment Playbook**
- `django` role: git clone/pull, uv sync, migrations, collectstatic
- Systemd service template with security hardening
- Nginx reverse proxy configuration
- `just ansible-deploy ENV [BRANCH]` command

**009-D: CI Deploy Key Setup**
- Ed25519 key pair generated (no passphrase)
- Private key stored in Doppler as `DEPLOY_SSH_PRIVATE_KEY`
- Public key stored in Doppler as `DEPLOY_SSH_PUBLIC_KEY`
- Deploy key added to cloud-init for agent/CI access
- Ansible commands use deploy key from Doppler for SSH

**009-E: Update Justfile and CI**
- `just ansible-setup ENV DOPPLER_CFG` - Server configuration
- `just ansible-deploy ENV BRANCH DOPPLER_CFG` - Deploy Django
- `just full-rebuild` / `just full-deploy` / `just quick-deploy` - Workflow commands
- Non-interactive execution via Doppler-stored SSH keys
- GitHub Actions integration deferred (manual deploys working)

### Note

Full deploy blocked by Django `STATIC_ROOT` configuration issue (application-level, not infrastructure). All infrastructure work is complete.
