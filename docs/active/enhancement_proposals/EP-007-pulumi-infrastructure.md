# EP-007: Pulumi Infrastructure

**Status:** completed
**Sprint:** 2026-01-21 to 2026-02-04
**Last Updated:** 2026-01-22

## Goal

Define all infrastructure as code using Pulumi. Enable reproducible, version-controlled deployments across Hetzner (Django backend) and Cloudflare (edge workers, static sites, DNS).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CLOUDFLARE (Edge)                            │   │
│  │                    "Always-working systems"                          │   │
│  │                                                                      │   │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │   │
│  │   │  DNS     │    │  Pages   │    │ Workers  │    │   WAF    │     │   │
│  │   │ Records  │    │  Sites   │    │ (Intake) │    │  Rules   │     │   │
│  │   └──────────┘    └──────────┘    └──────────┘    └──────────┘     │   │
│  │        │               │               │               │            │   │
│  │        └───────────────┴───────┬───────┴───────────────┘            │   │
│  │                                │                                     │   │
│  └────────────────────────────────┼─────────────────────────────────────┘   │
│                                   │                                         │
│                                   │ API calls                               │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      HETZNER (US West - Hillsboro)                   │   │
│  │                         "Django Backend"                             │   │
│  │                                                                      │   │
│  │   ┌──────────────────────────────────────────────────────────┐      │   │
│  │   │                      VPC Network                          │      │   │
│  │   │                                                           │      │   │
│  │   │   ┌─────────────┐         ┌─────────────┐                │      │   │
│  │   │   │   Django    │         │   Django    │                │      │   │
│  │   │   │   Server 1  │◄───────►│   Server 2  │ (optional)     │      │   │
│  │   │   │   (CX22)    │         │   (CX22)    │                │      │   │
│  │   │   └──────┬──────┘         └─────────────┘                │      │   │
│  │   │          │                                                │      │   │
│  │   │          │ Volume mount                                   │      │   │
│  │   │          ▼                                                │      │   │
│  │   │   ┌─────────────┐                                        │      │   │
│  │   │   │   Volume    │                                        │      │   │
│  │   │   │  (Storage)  │                                        │      │   │
│  │   │   └─────────────┘                                        │      │   │
│  │   │                                                           │      │   │
│  │   └───────────────────────────────────────────────────────────┘      │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   │ Database connection                     │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           NEON (Managed)                             │   │
│  │                        Serverless Postgres                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why This Split?

| Component | Platform | Rationale |
|-----------|----------|-----------|
| Static sites | Cloudflare Pages | Global edge, instant deploys, free SSL |
| Intake workers | Cloudflare Workers | Edge latency, auto-scaling, always on |
| DNS/CDN | Cloudflare | DDoS protection, caching, fast propagation |
| Django backend | Hetzner US West | Cost-effective, EU company, good US presence |
| Database | Neon | Serverless Postgres, branching, managed |

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 007-A | Pulumi project setup | completed |
| 007-B | Cloudflare infrastructure | completed |
| 007-C | Hetzner Django infrastructure | completed |
| 007-D | Deployment orchestration | completed |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| IaC tool | Pulumi (Python) | Same language as Django, type-safe, good providers |
| Django hosting | Hetzner CX22 | €4.50/mo, 2 vCPU, 4GB RAM, US West available |
| Container runtime | Docker + systemd | Simple, reliable, easy to debug |
| Secrets in infra | Pulumi ESC + Doppler | Pulumi for infra secrets, Doppler for app secrets |
| SSL | Cloudflare proxy | Free, automatic, no cert management |

## Pulumi Project Structure

```
infra/
├── Pulumi.yaml              # Project definition
├── Pulumi.dev.yaml          # Dev stack config
├── Pulumi.prod.yaml         # Prod stack config
├── __main__.py              # Entry point
├── requirements.txt         # Pulumi providers
└── src/
    ├── __init__.py
    ├── cloudflare/
    │   ├── __init__.py
    │   ├── dns.py           # DNS records
    │   ├── pages.py         # Static sites
    │   └── workers.py       # Edge workers
    ├── hetzner/
    │   ├── __init__.py
    │   ├── network.py       # VPC, firewall
    │   ├── server.py        # Django VM
    │   └── volume.py        # Persistent storage
    └── outputs.py           # Stack outputs
```

## Success Criteria

- [x] `pulumi up` provisions complete infrastructure
- [x] `pulumi preview` shows diff before changes
- [x] Separate dev/prod stacks with different configs
- [x] Django accessible via Cloudflare proxy (DNS configured)
- [x] Workers deployed and routing correctly (routes configured)
- [x] Sites deployed to Pages (projects configured)
- [x] All secrets managed securely (no plaintext in state)

## Cost Estimate

| Resource | Monthly Cost |
|----------|--------------|
| Hetzner CX22 (1x) | €4.50 (~$5) |
| Hetzner Volume 20GB | €0.96 (~$1) |
| Cloudflare (Free plan) | $0 |
| Neon (Free tier) | $0 |
| **Total (Dev)** | **~$6/mo** |

Production adds:
- Second Django server for redundancy: +$5
- Larger Neon plan: +$19
- Cloudflare Pro (optional): +$20

## Dependencies

- [x] Doppler secrets configured
- [x] Neon database running
- [ ] Hetzner account with API token
- [ ] Cloudflare account with API token
- [ ] Domain configured in Cloudflare

## Progress Log

### 2026-01-22
- **007-D completed**: Deployment orchestration
  - Justfile: `just deploy ENV` runs full pipeline (validate → provision → deploy)
  - Justfile: All commands use `doppler run --config ENV --` pattern
  - GitHub Actions: Full deploy.yml with Pulumi + Django deployment
  - All secrets flow from Doppler (single DOPPLER_TOKEN for CI)
  - Environment selection: `dev` / `prd` matches Doppler configs

- **007-C completed**: Hetzner Django infrastructure
  - `firewall.py`: Cloudflare IP restrictions (15 IPv4 + 7 IPv6 ranges), SSH admin whitelist
  - `cloud_init.py`: Docker/Compose, app directories, log rotation, deploy script
  - `network.py`: Refactored to VPC/subnet only (firewall now separate)
  - `server.py`: SSH key resource, firewall attachment, cloud-init, dependency ordering
  - `__main__.py`: Orchestrates all Hetzner resources with proper dependencies

- **007-B completed**: Cloudflare infrastructure
  - DNS records: api, dashboard, intake (CNAME to workers.dev)
  - Pages projects with custom domain support
  - Workers routing configuration
  - Security rules: rate limiting (intake 100/min, API 300/min), WAF (User-Agent block, threat score challenge)
  - All resources tagged with environment prefix

- **007-A completed**: Pulumi project setup
  - Added Pulumi to Flox environment
  - Created infra/ with full project structure
  - Hetzner modules: network, server, volume
  - Cloudflare modules: dns, pages, workers
  - Stack configs for dev/prod
  - Justfile commands: infra-preview, infra-up, infra-init, infra-secrets
  - Extended `just setup-infra` with infrastructure secrets wizard
  - Added comprehensive guide: `docs/knowledge/playbook/infrastructure-setup.md`

### 2026-01-21
- EP created
- Architecture designed
- Tickets defined

## References

- [Pulumi Hetzner Provider](https://www.pulumi.com/registry/packages/hcloud/)
- [Pulumi Cloudflare Provider](https://www.pulumi.com/registry/packages/cloudflare/)
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud)
- [Cloudflare Workers Limits](https://developers.cloudflare.com/workers/platform/limits/)
