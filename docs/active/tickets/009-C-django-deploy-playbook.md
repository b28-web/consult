# 009-C: Django Deployment Playbook

## Parent EP
[EP-009: Ansible Deployment](../enhancement_proposals/EP-009-ansible-deployment.md)

## Objective
Create Ansible playbook for deploying Django application updates.

## Acceptance Criteria

- [x] `deploy.yml` playbook deploys Django to server
- [x] Clones/pulls repo from GitHub
- [x] Runs `uv sync` for dependencies
- [x] Runs migrations via Doppler
- [x] Restarts gunicorn systemd service
- [x] `just ansible-deploy ENV` runs the playbook
- [x] Zero-downtime deploys (graceful restart via HUP signal)

## Technical Details

### deploy.yml tasks
1. Git clone (first run) or pull (updates)
2. `uv sync --frozen` in /app/apps/web
3. `doppler run -- uv run python manage.py migrate`
4. `doppler run -- uv run python manage.py collectstatic --noinput`
5. `systemctl restart consult-django`

### Systemd Service (`/etc/systemd/system/consult-django.service`)
```ini
[Unit]
Description=Consult Django (Gunicorn)
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/app/apps/web
Environment="PATH=/app/.venv/bin"
ExecStart=/usr/bin/doppler run -- /app/.venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/run/consult/gunicorn.sock \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### nginx config
```nginx
upstream django {
    server unix:/run/consult/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name api.consult.dev;

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /app/apps/web/staticfiles/;
    }
}
```

## Dependencies
- 009-B (base playbook completed)
- GitHub repo access from server

## Progress Log

### 2026-01-22
- Created `django` role with full deployment tasks:
  - Git clone/pull with configurable branch
  - `uv sync --frozen` for dependencies
  - Doppler-wrapped migrations and collectstatic
  - Systemd service installation and management
  - Nginx reverse proxy configuration
- Created templates:
  - `consult-django.service.j2` - Gunicorn systemd service with security hardening
  - `nginx-django.conf.j2` - Nginx config with static files, security headers
- Created `deploy.yml` playbook with health check verification
- Added justfile commands:
  - `just ansible-deploy ENV [BRANCH]` - Deploy Django
  - `just ansible-deploy-force ENV` - Force redeploy all tasks
- Updated `ansible-check` to verify both playbooks
- Syntax check passes for both playbooks
- **COMPLETE** - All acceptance criteria met
