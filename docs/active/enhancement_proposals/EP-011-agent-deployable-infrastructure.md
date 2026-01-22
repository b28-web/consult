# EP-011: Agent-Deployable Infrastructure

## Overview

Make the deployment flow fully runnable and debuggable by an LLM coding agent (Claude, etc.) without human intervention for common issues.

## Problem Statement

Currently, when deployments fail:
1. Agent cannot SSH to servers to inspect logs
2. Error messages require human interpretation
3. Interactive prompts block automation
4. No structured verification of each step
5. Agent must ask human to run commands and paste output

This creates slow, frustrating debugging cycles.

## Goals

1. **Agent SSH access** - Agent can SSH to servers using stored credentials
2. **Structured output** - All commands output machine-parseable success/failure
3. **No interactive prompts** - All commands can run non-interactively
4. **Step verification** - Each deployment step has clear pass/fail criteria
5. **Self-healing** - Common failures have automatic remediation

## Success Criteria

An LLM agent should be able to run:
```bash
just full-rebuild dev dev_personal
```

And either:
- Complete successfully with working Django at the target URL
- Fail with clear, actionable error that the agent can diagnose and fix

## Architecture

### SSH Access for Agent

```
┌─────────────┐     SSH Key      ┌─────────────┐
│   Agent     │ ───────────────► │   Server    │
│  (Claude)   │  from Doppler    │  (Hetzner)  │
└─────────────┘                  └─────────────┘
```

The agent retrieves SSH key from Doppler and uses it for:
- Running diagnostic commands
- Checking service logs
- Verifying deployment success

### Command Structure

All deployment commands follow this pattern:
```bash
just <command> ENV DOPPLER_CONFIG [OPTIONS]

# Examples:
just full-rebuild dev dev_personal      # Destroy + recreate + deploy
just full-deploy dev dev_personal       # Setup + deploy (no destroy)
just quick-deploy dev dev_personal      # Deploy code only
just server-logs dev dev_personal       # Get service logs
just server-status dev dev_personal     # Check service health
```

### Verification Steps

Each deployment phase has verification:

| Phase | Verification | Pass Criteria |
|-------|-------------|---------------|
| infra-up | Pulumi outputs | Server IP returned |
| ansible-setup | SSH test | Can connect as deploy user |
| ansible-deploy | Health check | HTTP 200 from /admin/login/ |

### Error Handling

Ansible playbooks capture and display:
- Service logs (journalctl)
- Nginx error logs
- Python tracebacks
- Configuration issues

## Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| 011-A | SSH key retrieval for agent | ✓ |
| 011-B | Non-interactive command verification | ✓ |
| 011-C | Structured error output from Ansible | ✓ |
| 011-D | Health check improvements | ✓ |
| 011-E | End-to-end agent test | ✓ |

## Technical Details

### 011-A: SSH Key Retrieval for Agent

Store deploy SSH key in Doppler, create justfile command to use it:

```bash
# Agent runs this to SSH
just agent-ssh dev dev_personal "journalctl -u consult-django -n 50"
```

Implementation:
- Fetch `DEPLOY_SSH_PRIVATE_KEY` from Doppler
- Write to temp file with proper permissions
- SSH using that key
- Clean up temp file

### 011-B: Non-Interactive Command Verification

Ensure all commands work without TTY:
- `just full-rebuild` with `--yes` flag or env var
- No `read -p` prompts in automated mode
- Exit codes reflect actual success/failure

### 011-C: Structured Error Output

Ansible outputs JSON-parseable error summaries:
```json
{
  "phase": "deploy",
  "task": "health_check",
  "status": "failed",
  "error": "HTTP 502 Bad Gateway",
  "logs": {
    "django": "...",
    "nginx": "..."
  },
  "suggestions": [
    "Check DOPPLER_SERVICE_TOKEN is set",
    "Verify gunicorn socket exists"
  ]
}
```

### 011-D: Health Check Improvements

Current health check just hits `/admin/login/`. Improve to:
- Check gunicorn socket exists
- Check systemd service is active
- Check nginx can proxy
- Report specific failure point

### 011-E: End-to-End Agent Test

Create a test script that simulates agent running full flow:
```bash
just agent-test-deploy dev dev_personal
```

This:
1. Destroys existing infra (if any)
2. Creates fresh infra
3. Runs setup
4. Deploys code
5. Verifies health
6. Reports success/failure with timing

## Out of Scope

- Multi-server deployments
- Blue/green deployments
- Automatic rollback (manual for now)

## Dependencies

- EP-009 (Ansible deployment) - mostly complete
- Doppler secrets configured
- Pulumi infrastructure working

## Risks

- SSH key in Doppler could be compromised → mitigate with key rotation procedure
- Agent could run destructive commands → mitigate with confirmation for destroy operations

## Completion Notes

**Completed: 2026-01-22**

### Implementation Summary

1. **Agent Commands Added to Justfile:**
   - `just agent-cmd ENV DOPPLER_CFG "command"` - Run single SSH command
   - `just agent-ssh ENV DOPPLER_CFG` - Interactive SSH session
   - `just agent-logs ENV DOPPLER_CFG` - Get Django service logs
   - `just agent-status ENV DOPPLER_CFG` - Get service status
   - `just agent-test-deploy ENV DOPPLER_CFG` - Full end-to-end test

2. **Non-Interactive Support:**
   - `CONFIRM=yes` env var bypasses confirmation prompts
   - `infra-destroy-yes` for auto-approve destroy
   - Exit codes: 3 (infra), 4 (setup), 5 (deploy), 6 (verify)

3. **Structured Output:**
   - JSON output from Ansible with status, logs, checks, suggestions
   - Dynamic suggestion engine for common errors
   - Sequential health checks identify exact failure point

4. **Infrastructure Changes:**
   - Deploy SSH key added to cloud-init for CI/agent access
   - Ansible uses Doppler key for non-interactive SSH
   - Fixed systemd ProtectHome to allow Doppler CLI access
   - Fixed POSIX shell compatibility (`. ` instead of `source`)

### Test Results

```
CONFIRM=yes just agent-test-deploy dev dev_personal

destroy: pass (33s)
create:  pass (69s)
setup:   pass (51s)
deploy:  FAIL - Django STATIC_ROOT not configured
```

### Remaining Issue

Full test is blocked by a Django application configuration issue (`STATIC_ROOT` not set in settings). This is not an infrastructure issue - the agent-deployable infrastructure work is complete.
