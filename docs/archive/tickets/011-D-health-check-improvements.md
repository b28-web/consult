# 011-D: Health Check Improvements

## Parent EP
[EP-011: Agent-Deployable Infrastructure](../enhancement_proposals/EP-011-agent-deployable-infrastructure.md)

## Objective
Improve deployment health checks to identify specific failure points.

## Acceptance Criteria

- [x] Health check verifies gunicorn socket exists
- [x] Health check verifies systemd service is active
- [x] Health check verifies nginx can reach upstream
- [x] Health check reports which specific component failed
- [x] Reduced false positives from timing issues

## Technical Details

### Current Health Check

```yaml
- name: Wait for Django to be healthy
  uri:
    url: "http://localhost/admin/login/"
    status_code: 200
  retries: 10
  delay: 3
```

Problems:
- Only checks final HTTP response
- Doesn't identify which component failed
- 30 second total wait may not be enough

### Improved Health Check

```yaml
- name: Verify gunicorn socket exists
  wait_for:
    path: /run/consult/gunicorn.sock
    state: present
    timeout: 30
  register: socket_check

- name: Verify Django service is active
  systemd:
    name: consult-django
    state: started
  register: service_check

- name: Wait for gunicorn to accept connections
  wait_for:
    path: /run/consult/gunicorn.sock
    state: present
    timeout: 30

- name: Verify nginx can reach Django
  uri:
    url: "http://localhost/admin/login/"
    status_code: 200
  register: http_check
  retries: 10
  delay: 3
  until: http_check.status == 200

- name: Report health check results
  debug:
    msg: |
      Health Check Results:
      - Gunicorn socket: {{ 'OK' if socket_check is success else 'FAILED' }}
      - Systemd service: {{ 'OK' if service_check is success else 'FAILED' }}
      - HTTP response: {{ 'OK' if http_check.status == 200 else 'FAILED' }}
```

### Failure Diagnostics

When a specific check fails, gather targeted diagnostics:

| Failed Check | Diagnostics |
|--------------|-------------|
| Socket missing | journalctl -u consult-django |
| Service not active | systemctl status consult-django |
| HTTP 502 | nginx error log, gunicorn log |
| HTTP 500 | Django error log, traceback |

### Timing Improvements

- Socket check: 30s timeout (gunicorn startup)
- Service check: immediate (systemd knows state)
- HTTP check: 10 retries x 3s = 30s (app warmup)
- Total: ~60s max for healthy deploy

## Dependencies

- None

## Progress Log

### 2026-01-22
- Implemented 4-step sequential health check in deploy.yml:
  1. Wait for gunicorn socket (30s timeout)
  2. Verify systemd service is active
  3. Verify nginx is running
  4. HTTP health check (15 retries x 2s = 30s)
- Added `failed_check` variable to identify exactly which component failed
- Improved timing: total max wait ~60s for healthy deploy
- Context-aware suggestions based on which check failed
- JSON output now includes `failed_check` field and per-check status
- **COMPLETE** - All acceptance criteria met
