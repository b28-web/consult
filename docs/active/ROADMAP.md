# Roadmap

Current priorities and planned work for Consult.

## Active Sprints

### EP-001: Backend Foundation
Get the full stack working end-to-end.

| Ticket | Title | Status |
|--------|-------|--------|
| 001-A | Django backend bootstrap | completed |
| 001-B | Intake worker deployment | in-progress |
| 001-C | First client site (coffee-shop) | in-progress |

### EP-006: Automated Deploy Validation
Create agent-driven pre-deploy validation pipeline with Dagger.

| Ticket | Title | Status |
|--------|-------|--------|
| 006-A | Dagger pipeline setup | pending |
| 006-B | Pre-deploy validation flow | pending |
| 006-C | GitHub Actions integration | pending |

### EP-007: Pulumi Infrastructure
Infrastructure as code for Hetzner (Django) + Cloudflare (edge).

| Ticket | Title | Status |
|--------|-------|--------|
| 007-A | Pulumi project setup | pending |
| 007-B | Cloudflare infrastructure | pending |
| 007-C | Hetzner Django infrastructure | pending |
| 007-D | Deployment orchestration | pending |

## Planned Sprints

### EP-002: Submission Processing & Dashboard
Build the core inbox experience with AI classification.

| Ticket | Title | Status |
|--------|-------|--------|
| 002-A | Submission processing task | pending |
| 002-B | BAML classification integration | pending |
| 002-C | Dashboard shell with auth | pending |
| 002-D | Inbox list view (HTMX) | pending |
| 002-E | Message detail panel (HTMX) | pending |
| 002-F | Contact profile view | pending |

### EP-003: Communications (Twilio + Resend)
Enable two-way messaging: SMS, voicemail, email.

| Ticket | Title | Status |
|--------|-------|--------|
| 003-A | Twilio SMS webhook handling | pending |
| 003-B | Twilio voicemail handling | pending |
| 003-C | Twilio signature validation | pending |
| 003-D | Outbound SMS via Twilio | pending |
| 003-E | Outbound email via Resend | pending |
| 003-F | Reply channel selection logic | pending |

### EP-004: External Integrations (Cal.com + Jobber)
Connect scheduling and CRM tools.

| Ticket | Title | Status |
|--------|-------|--------|
| 004-A | Cal.com embed component | pending |
| 004-B | Cal.com webhook handler | pending |
| 004-C | Jobber OAuth integration | pending |
| 004-D | Jobber webhook sync | pending |
| 004-E | Integration settings UI | pending |

### EP-005: Client Sites at Scale
Deploy all client sites with automation.

| Ticket | Title | Status |
|--------|-------|--------|
| 005-A | Site scaffolding script | pending |
| 005-B | Deploy coffee-shop site | pending |
| 005-C | Deploy hauler site (+ Cal.com) | pending |
| 005-D | Deploy cleaning site | pending |
| 005-E | Deploy landscaper site | pending |
| 005-F | Deploy barber site | pending |
| 005-G | Deploy data-analytics site | pending |
| 005-H | Deploy web-dev site | pending |
| 005-I | Deploy local-agency site | pending |
| 005-J | CI/CD pipeline for sites | pending |

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
