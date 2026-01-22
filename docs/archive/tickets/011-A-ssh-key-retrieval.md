# 011-A: SSH Key Retrieval for Agent

## Parent EP
[EP-011: Agent-Deployable Infrastructure](../enhancement_proposals/EP-011-agent-deployable-infrastructure.md)

## Objective
Enable LLM agent to SSH to servers using credentials from Doppler.

## Acceptance Criteria

- [x] `DEPLOY_SSH_PRIVATE_KEY` stored in Doppler (done in 009-D)
- [x] `just agent-ssh` command retrieves key and connects
- [x] `just agent-cmd` runs single command via SSH
- [x] Key is cleaned up after use (not left on disk)
- [x] Works without interactive prompts (BatchMode=yes)

## Technical Details

### Justfile Commands

```bash
# Interactive SSH session
just agent-ssh dev dev_personal

# Run single command
just agent-cmd dev dev_personal "sudo journalctl -u consult-django -n 50"

# Common shortcuts
just agent-logs dev dev_personal          # Django logs
just agent-status dev dev_personal        # Service status
```

### Implementation

```bash
agent-cmd ENV="dev" DOPPLER_CONFIG="" CMD="":
    #!/usr/bin/env bash
    set -euo pipefail

    DOPPLER_CFG="{{DOPPLER_CONFIG}}"
    if [ -z "$DOPPLER_CFG" ]; then DOPPLER_CFG="{{ENV}}"; fi

    # Get server IP
    SERVER_IP=$(cd infra && doppler run --config "$DOPPLER_CFG" -- \
        pulumi stack output django_server_ip --stack "$(just _stack {{ENV}})")

    # Get SSH key from Doppler
    SSH_KEY=$(doppler secrets get DEPLOY_SSH_PRIVATE_KEY --plain --config "$DOPPLER_CFG")

    # Write to temp file
    KEY_FILE=$(mktemp)
    echo "$SSH_KEY" > "$KEY_FILE"
    chmod 600 "$KEY_FILE"

    # Run command
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no deploy@"$SERVER_IP" "{{CMD}}"

    # Cleanup
    rm -f "$KEY_FILE"
```

### Security Notes

- Key only exists in memory/temp file during command execution
- Temp file has 600 permissions
- Key is deleted immediately after use
- `StrictHostKeyChecking=no` for automation (server IP may change on rebuild)

## Dependencies

- DEPLOY_SSH_PRIVATE_KEY in Doppler (done in 009-D)
- Server has deploy user with key in authorized_keys

## Progress Log

### 2026-01-22
- Added `agent-cmd` command to justfile - runs single command via SSH using key from Doppler
- Added `agent-ssh` command - interactive SSH session using Doppler key
- Added `agent-logs` shortcut - fetches Django service logs
- Added `agent-status` shortcut - fetches systemd service status
- Security: Key written to temp file with 600 permissions, cleaned up via trap on exit
- Non-interactive: Uses BatchMode=yes and StrictHostKeyChecking=no
- **COMPLETE** - All acceptance criteria met
