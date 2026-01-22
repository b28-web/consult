# 011-B: Non-Interactive Command Verification

## Parent EP
[EP-011: Agent-Deployable Infrastructure](../enhancement_proposals/EP-011-agent-deployable-infrastructure.md)

## Objective
Ensure all deployment commands can run without interactive prompts or TTY.

## Acceptance Criteria

- [x] `just full-rebuild` works with `CONFIRM=yes` env var
- [x] All `read -p` prompts have non-interactive bypass
- [x] Exit codes accurately reflect success (0) or failure (non-zero)
- [x] Commands work when piped or run from scripts
- [x] No TTY-dependent output formatting

## Technical Details

### Environment Variable Overrides

```bash
# Skip confirmation prompts
CONFIRM=yes just full-rebuild dev dev_personal

# Or via justfile parameter
just full-rebuild dev dev_personal --confirm
```

### Commands to Audit

| Command | Interactive? | Fix |
|---------|-------------|-----|
| full-rebuild | Yes (Type 'yes') | CONFIRM env var |
| infra-destroy | Yes (Pulumi prompt) | Already has --yes |
| ansible-* | No | OK |
| server-ssh | Yes (interactive) | OK (agent-cmd for non-interactive) |

### Implementation Pattern

```bash
# Before
read -p "Are you sure? Type 'yes': " confirm
if [ "$confirm" != "yes" ]; then exit 1; fi

# After
if [ "${CONFIRM:-}" = "yes" ]; then
    echo "CONFIRM=yes, proceeding..."
else
    read -p "Are you sure? Type 'yes': " confirm
    if [ "$confirm" != "yes" ]; then exit 1; fi
fi
```

### Exit Code Contract

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General failure |
| 2 | Configuration error (missing secrets, etc.) |
| 3 | Infrastructure error (Pulumi failed) |
| 4 | Setup error (Ansible setup failed) |
| 5 | Deploy error (Ansible deploy failed) |
| 6 | Health check failed |

## Dependencies

- None

## Progress Log

### 2026-01-22
- Added `CONFIRM=yes` env var support to `full-rebuild`
- Added `infra-destroy-yes` command for non-interactive infrastructure destroy
- Added specific exit codes to deployment commands:
  - Exit 3: Infrastructure error (Pulumi failed)
  - Exit 4: Setup error (Ansible setup failed)
  - Exit 5: Deploy error (Ansible deploy failed)
- Updated `full-deploy` and `quick-deploy` with proper exit codes
- All commands now work without TTY (use BatchMode for SSH)
- **COMPLETE** - All acceptance criteria met
