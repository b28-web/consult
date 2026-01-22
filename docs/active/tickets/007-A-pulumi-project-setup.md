# 007-A: Pulumi Project Setup

**EP:** [EP-007-pulumi-infrastructure](../enhancement_proposals/EP-007-pulumi-infrastructure.md)
**Status:** completed

## Summary

Initialize Pulumi project with Python SDK, configure providers for Hetzner and Cloudflare, set up dev/prod stacks with proper secret management.

## Acceptance Criteria

- [x] `infra/` directory with Pulumi project
- [x] Pulumi CLI added to Flox environment
- [x] Hetzner provider configured
- [x] Cloudflare provider configured
- [x] Dev stack created (`pulumi stack init dev`)
- [x] Prod stack created (`pulumi stack init prod`)
- [x] Secrets use Pulumi ESC or encrypted config
- [x] `just infra-preview` and `just infra-up` commands

## Implementation Notes

### Flox Environment

Add to `.flox/env/manifest.toml`:
```toml
[install]
pulumi.pkg-path = "pulumi"
```

### Project Initialization

```bash
mkdir -p infra
cd infra
pulumi new python --name consult-infra --description "Consult infrastructure"
```

### Provider Setup

`infra/requirements.txt`:
```
pulumi>=3.0.0
pulumi-hcloud>=1.0.0
pulumi-cloudflare>=5.0.0
pulumi-command>=0.9.0
```

### Stack Configuration

`infra/Pulumi.dev.yaml`:
```yaml
config:
  consult-infra:environment: dev
  hcloud:token:
    secure: <encrypted>
  cloudflare:apiToken:
    secure: <encrypted>
```

`infra/Pulumi.prod.yaml`:
```yaml
config:
  consult-infra:environment: prod
  hcloud:token:
    secure: <encrypted>
  cloudflare:apiToken:
    secure: <encrypted>
```

### Entry Point

`infra/__main__.py`:
```python
"""Consult Infrastructure - Pulumi Entry Point"""

import pulumi

from src.cloudflare import dns, pages, workers
from src.hetzner import network, server, volume
from src import outputs

# Get environment from stack config
config = pulumi.Config()
env = config.require("environment")

# Export outputs for other tools
pulumi.export("environment", env)
```

### Justfile Commands

```just
# Preview infrastructure changes
infra-preview STACK="dev":
    cd infra && pulumi preview --stack {{STACK}}

# Apply infrastructure changes
infra-up STACK="dev":
    cd infra && pulumi up --stack {{STACK}}

# Destroy infrastructure (careful!)
infra-destroy STACK="dev":
    cd infra && pulumi destroy --stack {{STACK}}

# Show infrastructure outputs
infra-outputs STACK="dev":
    cd infra && pulumi stack output --stack {{STACK}} --json
```

### Secret Management

Provider tokens stored as encrypted Pulumi config:

```bash
# Set Hetzner token (encrypted in stack config)
pulumi config set --secret hcloud:token "your-token"

# Set Cloudflare token
pulumi config set --secret cloudflare:apiToken "your-token"
```

App secrets (DATABASE_URL, etc.) stay in Doppler - Pulumi only manages infra secrets.

## Progress

### 2026-01-22
- Added `pulumi` and `pulumi-language-python` to Flox environment
- Created `infra/` directory with full Pulumi project structure:
  - `Pulumi.yaml` - project definition
  - `requirements.txt` - provider dependencies (hcloud, cloudflare, command)
  - `__main__.py` - entry point orchestrating all infrastructure
  - `src/hetzner/` - network, server, volume modules
  - `src/cloudflare/` - dns, pages, workers modules
  - `src/outputs.py` - stack outputs
- Created `Pulumi.dev.yaml` and `Pulumi.prod.yaml` stack configs
- Added Justfile commands: `infra-preview`, `infra-up`, `infra-destroy`, `infra-outputs`, `infra-refresh`, `infra-init`, `infra-secrets`
- Extended `just setup-infra` wizard with:
  - Hetzner API token configuration
  - Cloudflare API token, account ID, zone ID
  - SSH key setup (detect existing or generate new)
  - Domain configuration
  - Automatic Pulumi stack configuration from Doppler
- Created comprehensive guide: `docs/knowledge/playbook/infrastructure-setup.md`
- **Status: Complete** - ready for secrets configuration and first deploy
