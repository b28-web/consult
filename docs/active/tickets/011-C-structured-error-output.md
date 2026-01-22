# 011-C: Structured Error Output from Ansible

## Parent EP
[EP-011: Agent-Deployable Infrastructure](../enhancement_proposals/EP-011-agent-deployable-infrastructure.md)

## Objective
Make Ansible output machine-parseable error information that an LLM agent can understand and act on.

## Acceptance Criteria

- [x] Failed deployments output JSON error summary
- [x] Error includes relevant logs (Django, nginx)
- [x] Error includes actionable suggestions
- [x] Success outputs confirmation with key details
- [x] Output works with both human and machine readers

## Technical Details

### Error Output Format

On failure, Ansible outputs:
```
═══ DEPLOYMENT FAILED ═══

{
  "status": "failed",
  "phase": "health_check",
  "task": "Wait for Django to be healthy",
  "error": "HTTP 502 Bad Gateway after 10 retries",
  "server": "5.78.137.79",
  "logs": {
    "django_service": "... last 20 lines ...",
    "nginx_error": "... last 10 lines ..."
  },
  "checks": {
    "gunicorn_socket": false,
    "systemd_active": false,
    "nginx_running": true
  },
  "suggestions": [
    "Gunicorn is not running - check DOPPLER_SERVICE_TOKEN",
    "Run: just agent-logs dev dev_personal",
    "Run: just agent-cmd dev dev_personal 'sudo systemctl status consult-django'"
  ]
}
```

### Success Output Format

```
═══ DEPLOYMENT SUCCESSFUL ═══

{
  "status": "success",
  "server": "5.78.137.79",
  "url": "http://dev.consult.example.com",
  "admin_url": "http://dev.consult.example.com/admin/",
  "git_branch": "main",
  "git_commit": "abc1234",
  "timing": {
    "total": "127s",
    "setup": "45s",
    "deploy": "82s"
  }
}
```

### Ansible Implementation

Update `ansible/playbooks/deploy.yml` post_tasks:

```yaml
- name: Collect diagnostic info on failure
  block:
    - name: Get gunicorn socket status
      stat:
        path: /run/consult/gunicorn.sock
      register: gunicorn_socket

    - name: Get systemd service status
      shell: systemctl is-active consult-django || true
      register: systemd_status

    - name: Get Django logs
      shell: journalctl -u consult-django -n 20 --no-pager
      register: django_logs

    - name: Get nginx error logs
      shell: tail -10 /var/log/nginx/error.log
      register: nginx_logs

    - name: Output structured error
      debug:
        msg: "{{ lookup('template', 'error_report.json.j2') }}"
  when: health_check.failed | default(false)
```

### Suggestion Engine

Map common errors to suggestions:

| Error Pattern | Suggestion |
|--------------|------------|
| "502 Bad Gateway" | Check gunicorn is running |
| "Doppler Error: token" | Verify DOPPLER_SERVICE_TOKEN |
| "Permission denied" | Check file ownership in /app |
| "Module not found" | Run uv sync, check dependencies |
| "Database connection" | Verify DATABASE_URL in Doppler |

## Dependencies

- 011-A (SSH access for detailed diagnostics)

## Progress Log

### 2026-01-22
- Updated `ansible/playbooks/deploy.yml` with structured JSON output
- On failure: JSON includes status, phase, task, error, server, logs (django + nginx), checks (gunicorn_socket, systemd_active, nginx_running), and suggestions
- On success: JSON includes status, server, url, admin_url, git_branch, git_commit
- Added dynamic suggestion engine that detects:
  - Missing gunicorn socket
  - Systemd service not active
  - Doppler errors
  - Python module errors
  - Database errors
- Updated `ansible/playbooks/setup.yml` with structured success output
- **COMPLETE** - All acceptance criteria met
