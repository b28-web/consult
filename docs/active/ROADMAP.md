# Roadmap

Current priorities and planned work for Consult.

## Active Sprints

*No active sprints. See Completed Sprints below.*

---

## Completed Sprints

### EP-008: Restaurant Client Type with POS Integration ✓
Full restaurant stack with POS integration, online ordering, and payments.

| Phase | Tickets | Status |
|-------|---------|--------|
| Phase 1: Foundation | 008-A, 008-B, 008-C, 008-D | ✓ |
| Phase 2: POS Read Integration | 008-E, 008-F | ✓ |
| Phase 3: Additional POS Providers | 008-G, 008-H | ✓ |
| Phase 4: Online Ordering | 008-I, 008-J, 008-K, 008-L | ✓ |
| Phase 5: Demo Deployment | 008-M | ✓ |

**Completed 2026-01-24**: Full restaurant platform with:
- POS adapter architecture (Toast, Clover, Square + Mock)
- Restaurant domain models (Menu, MenuItem, ModifierGroup, Modifier, Order)
- Menu API with availability polling for 86'd items
- Restaurant site template with cart/checkout
- Stripe payment integration
- Demo site deployed: https://consult-katies-sushi.pages.dev

### EP-010: Doppler CI Configuration ✓
Fix Doppler configuration so CI/CD workflows can deploy.

| Ticket | Title | Status |
|--------|-------|--------|
| 010-A | Create dev/prd configs in Doppler | ✓ |
| 010-B | Update GitHub DOPPLER_TOKEN | ✓ |
| 010-C | Verify Deploy Sites workflow | ✓ |

**Completed 2026-01-22**: CI/CD pipeline unblocked with:
- `dev` config created in Doppler (cloned from `dev_personal`)
- Service token created and added to GitHub Actions
- Cloudflare Pages project `consult-coffee-shop` created
- Deploy Sites workflow verified working (run #21272963174)

### EP-005: Client Sites at Scale ✓
Deploy 8 service/B2B client sites with scaffolding and registry-based deployment.

| Ticket | Title | Status |
|--------|-------|--------|
| 005-A | Site scaffolding + registry system | ✓ |
| 005-B | Deploy coffee-shop site (cafe) | ✓ |
| 005-C | Deploy hauler site (+ Cal.com) | ✓ |
| 005-D | Deploy cleaning site | ✓ |
| 005-E | Deploy landscaper site | ✓ |
| 005-F | Template hardening (mobile, CSS) | ✓ |
| 005-G | Deploy barber site | ✓ |
| 005-H | Deploy data-analytics site | ✓ |
| 005-I | Deploy webstudio site | ✓ |
| 005-J | Deploy local-agency site | ✓ |
| 005-K | CI/CD pipeline for sites | ✓ |

**Completed 2026-01-22**: Full site deployment pipeline with:
- Site scaffolding script with industry presets
- Site registry system (`sites/registry.yaml`)
- Deploy wizard (`just deploy-wizard`)
- CI/CD pipeline (`.github/workflows/deploy-sites.yml`)
- 8 sites deployed: coffee-shop, hauler, cleaning, landscaper, barber, data-analytics, webstudio, local-agency

### EP-004: External Integrations (Cal.com + Jobber) ✓
Connect scheduling and CRM tools.

| Ticket | Title | Status |
|--------|-------|--------|
| 004-A | Cal.com embed component | ✓ |
| 004-B | Cal.com webhook handler | ✓ |
| 004-C | Jobber OAuth integration | ✓ |
| 004-D | Jobber webhook sync | ✓ |
| 004-E | Integration settings UI | ✓ |

**Completed 2026-01-22**: Full Cal.com + Jobber integration with:
- CalEmbed.astro component for booking widgets
- Cal.com webhook handler for booking sync
- Jobber OAuth flow with token refresh
- Jobber webhook handler for job/client sync
- Dashboard settings page for managing integrations

### EP-003: Communications (Twilio + Resend) ✓
Enable two-way messaging: SMS, voicemail, email.

| Ticket | Title | Status |
|--------|-------|--------|
| 003-A | Twilio SMS webhook handling | ✓ |
| 003-B | Twilio voicemail handling | ✓ |
| 003-C | Twilio signature validation | ✓ |
| 003-D | Outbound SMS via Twilio | ✓ |
| 003-E | Outbound email via Resend | ✓ |
| 003-F | Reply channel selection logic | ✓ |

**Completed 2026-01-22**: Full two-way communication with:
- Inbound SMS/MMS webhook handling with signature validation
- Voicemail recording with Twilio transcription
- Outbound SMS via Twilio API
- Outbound email via Resend API
- Smart reply channel defaults based on original message

### EP-002: Submission Processing & Dashboard ✓
Build the core inbox experience with AI classification.

| Ticket | Title | Status |
|--------|-------|--------|
| 002-A | Submission processing task | ✓ |
| 002-B | BAML classification integration | ✓ |
| 002-C | Dashboard shell with auth | ✓ |
| 002-D | Inbox list view (HTMX) | ✓ |
| 002-E | Message detail panel (HTMX) | ✓ |
| 002-F | Contact profile view | ✓ |

**Completed 2026-01-22**: Full inbox experience with:
- Submission processing and AI classification (BAML + Gemini)
- Dashboard shell with DaisyUI + HTMX
- Inbox list with urgency sorting and filters
- Message detail panel with contact history
- Contact profile with search, inline edit, notes

---

### EP-011: Agent-Deployable Infrastructure ✓
Make deployment flow fully runnable by LLM coding agents. Enables autonomous debugging and deployment.

| Ticket | Title | Status |
|--------|-------|--------|
| 011-A | SSH key retrieval for agent | ✓ |
| 011-B | Non-interactive command verification | ✓ |
| 011-C | Structured error output from Ansible | ✓ |
| 011-D | Health check improvements | ✓ |
| 011-E | End-to-end agent test | ✓ |

**Completed 2026-01-22**: Agent can now:
- SSH to servers using `just agent-cmd` with Doppler-stored keys
- Run `CONFIRM=yes just agent-test-deploy` for full end-to-end testing
- Get structured JSON error output with actionable suggestions
- Debug failures without human intervention

Full end-to-end test passes: destroy → create → setup → deploy → verify (~187s).

---

### EP-009: Ansible Deployment ✓
Ansible for Django deployment to Hetzner. Docker for local dev/testing only (no container registry).

| Ticket | Title | Status |
|--------|-------|--------|
| 009-A | Local Docker setup | ✓ |
| 009-B | Ansible inventory and base playbook | ✓ |
| 009-C | Django deployment playbook | ✓ |
| 009-D | CI deploy key setup | ✓ |
| 009-E | Update justfile and CI | ✓ |

**Completed 2026-01-22**:
- `just dev` → Docker Compose for local development
- `just ansible-deploy ENV BRANCH DOPPLER_CFG` → Ansible deploys to Hetzner
- `just full-rebuild` / `just full-deploy` / `just quick-deploy` workflow commands
- Passwordless deploy key for CI (via Doppler DEPLOY_SSH_PRIVATE_KEY)
- Doppler service token auth for server

Full deployment working end-to-end.

---

### EP-007: Pulumi Infrastructure ✓
Infrastructure as code for Hetzner (Django) + Cloudflare (edge).

| Ticket | Title | Status |
|--------|-------|--------|
| 007-A | Pulumi project setup | ✓ |
| 007-B | Cloudflare infrastructure | ✓ |
| 007-C | Hetzner Django infrastructure | ✓ |
| 007-D | Deployment orchestration | ✓ |

**Completed 2026-01-22**: Infrastructure as code with Pulumi (Hetzner + Cloudflare), Doppler as single secret store. Django app deployment deferred to EP-009 (Ansible).

### EP-001: Backend Foundation ✓
Get the full stack working end-to-end.

| Ticket | Title | Status |
|--------|-------|--------|
| 001-A | Django backend bootstrap | ✓ |
| 001-B | Intake worker deployment | ✓ |
| 001-C | First client site (coffee-shop) | ✓ |

**Completed 2026-01-22**: Full stack verified with `just test-local`.

### EP-006: Automated Deploy Validation ✓
Create agent-driven pre-deploy validation pipeline with Dagger.

| Ticket | Title | Status |
|--------|-------|--------|
| 006-A | Dagger pipeline setup | ✓ |
| 006-B | Pre-deploy validation flow | ✓ |
| 006-C | GitHub Actions integration | ✓ |

**Completed 2026-01-21**: Full Dagger pipeline with parallel execution, JSON output, and GitHub Actions integration.

## Icebox

Ideas not yet planned:
- Billing/subscription management (Stripe)
- Analytics dashboard
- White-label admin portal
- Mobile app for staff
- Inbound email parsing
- AI-generated reply suggestions

---

## Structure

```
docs/active/
├── ROADMAP.md                           # You are here
├── enhancement_proposals/
│   └── EP-NNN-slug.md                   # Sprint = multiple tickets
└── tickets/
    └── NNN-X-slug.md                    # Single work item in an EP

docs/archive/                            # Completed EPs and tickets
docs/knowledge/
├── patterns/                            # How things work
└── playbook/                            # Copy-paste prompts
```

**Naming:**
- EP: `EP-NNN-slug` (e.g., EP-001-backend-foundation)
- Tickets: `NNN-X-slug` where NNN matches EP, X is A/B/C (e.g., 001-A-django-bootstrap)
