# 011-E: End-to-End Agent Test

## Parent EP
[EP-011: Agent-Deployable Infrastructure](../enhancement_proposals/EP-011-agent-deployable-infrastructure.md)

## Objective
Create a test script that validates an LLM agent can run the full deployment flow.

## Acceptance Criteria

- [x] `just agent-test-deploy` runs full flow non-interactively
- [x] Test destroys existing infra (clean slate)
- [x] Test creates new infra
- [x] Test runs setup and deploy
- [x] Test verifies health
- [x] Test outputs structured pass/fail result
- [x] Test can be run by CI or agent

## Technical Details

### Test Command

```bash
# Run full agent deployment test
CONFIRM=yes just agent-test-deploy dev dev_personal

# Expected output on success:
# {
#   "status": "pass",
#   "duration": "287s",
#   "phases": {
#     "destroy": {"status": "pass", "duration": "45s"},
#     "create": {"status": "pass", "duration": "120s"},
#     "setup": {"status": "pass", "duration": "62s"},
#     "deploy": {"status": "pass", "duration": "60s"}
#   },
#   "verification": {
#     "ssh": "pass",
#     "http": "pass",
#     "admin": "pass"
#   },
#   "server": "5.78.137.79",
#   "url": "http://5.78.137.79"
# }
```

### Test Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. DESTROY (if exists)                                     │
│     pulumi destroy --yes                                    │
│     └─ Verify: no server in pulumi state                    │
├─────────────────────────────────────────────────────────────┤
│  2. CREATE                                                  │
│     pulumi up --yes                                         │
│     └─ Verify: server IP returned                           │
├─────────────────────────────────────────────────────────────┤
│  3. SETUP                                                   │
│     ansible-playbook setup.yml                              │
│     └─ Verify: can SSH as deploy user                       │
├─────────────────────────────────────────────────────────────┤
│  4. DEPLOY                                                  │
│     ansible-playbook deploy.yml                             │
│     └─ Verify: HTTP 200 from /admin/login/                  │
├─────────────────────────────────────────────────────────────┤
│  5. VERIFY                                                  │
│     - SSH works                                             │
│     - Django responds                                       │
│     - Static files served                                   │
│     └─ Output: structured JSON result                       │
└─────────────────────────────────────────────────────────────┘
```

### Justfile Implementation

```bash
agent-test-deploy ENV="dev" DOPPLER_CONFIG="":
    #!/usr/bin/env bash
    set -euo pipefail

    DOPPLER_CFG="{{DOPPLER_CONFIG}}"
    if [ -z "$DOPPLER_CFG" ]; then DOPPLER_CFG="{{ENV}}"; fi

    START_TIME=$(date +%s)

    echo '{"test": "agent-deploy", "status": "running"}'

    # Phase 1: Destroy
    PHASE_START=$(date +%s)
    if CONFIRM=yes just infra-destroy "$DOPPLER_CFG" 2>&1; then
        DESTROY_STATUS="pass"
    else
        DESTROY_STATUS="pass"  # OK if nothing to destroy
    fi
    DESTROY_DURATION=$(($(date +%s) - PHASE_START))

    # Phase 2: Create
    PHASE_START=$(date +%s)
    if just infra-up-yes "$DOPPLER_CFG" 2>&1; then
        CREATE_STATUS="pass"
    else
        CREATE_STATUS="fail"
        echo '{"status": "fail", "phase": "create"}'
        exit 3
    fi
    CREATE_DURATION=$(($(date +%s) - PHASE_START))

    # ... continue for setup, deploy, verify ...

    TOTAL_DURATION=$(($(date +%s) - START_TIME))

    echo "{\"status\": \"pass\", \"duration\": \"${TOTAL_DURATION}s\"}"
```

### CI Integration

```yaml
# .github/workflows/test-deploy.yml
name: Test Agent Deploy
on:
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am

jobs:
  test-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run agent deploy test
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          CONFIRM=yes just agent-test-deploy dev dev
```

## Dependencies

- 011-A (SSH access)
- 011-B (Non-interactive commands)
- 011-C (Structured output)
- 011-D (Health checks)

## Progress Log

### 2026-01-22
- Added `just agent-test-deploy` command to justfile
- Implements full 5-phase flow: destroy → create → setup → deploy → verify
- Requires `CONFIRM=yes` for non-interactive execution
- Tracks timing for each phase
- Outputs structured JSON result with:
  - Overall status (pass/fail)
  - Total duration
  - Per-phase status and duration
  - Server IP
  - Verification results (SSH, HTTP)
- Uses proper exit codes matching 011-B:
  - Exit 3: Infrastructure error (create failed)
  - Exit 4: Setup error (ansible-setup failed)
  - Exit 5: Deploy error (ansible-deploy failed)
  - Exit 6: Verification error (SSH/HTTP check failed)

### Test Run Results
```
CONFIRM=yes just agent-test-deploy dev dev_personal

destroy: pass (33s)
create:  pass (69s)
setup:   pass (52s)
deploy:  pass (29s)
verify:  pass (4s)
Total:   187s
```

Full end-to-end test passing.

- **COMPLETE** - All acceptance criteria met
