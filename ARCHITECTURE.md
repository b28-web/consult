# Architecture

This document describes the system architecture for the Consult platform.

## Overview

Consult is a multi-tenant web agency platform that provides:
- **Static marketing sites** for clients (Astro + Sanity CMS)
- **Unified inbox** for all client communications (web forms, SMS, voicemail)
- **CRM and scheduling** integrated with existing tools (Jobber, etc.)

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Traffic                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ Astro Sites  │ │   Twilio     │ │  Web Forms   │
            │ (CF Pages)   │ │ SMS/Voice    │ │              │
            └──────────────┘ └──────────────┘ └──────────────┘
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                         ┌────────────────────┐
                         │ Cloudflare Workers │
                         │  (Intake Layer)    │
                         └────────────────────┘
                                     │
                                     ▼
                         ┌────────────────────┐
                         │   Neon Postgres    │
                         │   (submissions)    │
                         └────────────────────┘
                                     │
                                     ▼
                         ┌────────────────────┐
                         │   Django Backend   │
                         │  (Processing &     │
                         │   Dashboard)       │
                         └────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  AI / BAML   │ │   Jobber     │ │   Mailgun    │
            │ Classification│ │    Sync      │ │   (Email)    │
            └──────────────┘ └──────────────┘ └──────────────┘
```

## Components

### Cloudflare Workers (Intake Layer)

Fast, edge-deployed workers that accept all inbound traffic:
- Web form submissions
- Twilio webhooks (SMS, voice)
- Integration webhooks

Workers do minimal validation and write directly to the `submissions` table.
**Design goal**: < 50ms response time, no processing at the edge.

Location: `/workers/`

### Django Backend

The core application handling:
- Submission processing (classify, create contacts/messages)
- Dashboard (inbox, CRM views)
- Multi-tenant data isolation
- Integration syncing (Jobber, etc.)

Location: `/apps/web/`

### Astro Sites

Static marketing sites for each client:
- Built from Sanity CMS content
- Deployed to Cloudflare Pages
- Forms POST to intake workers

Location: `/sites/`

### Neon Postgres

Serverless Postgres with:
- Connection pooling via PgBouncer
- Branch databases for development
- Point-in-time recovery

## Multi-Tenancy Model

Every data record is scoped to a `Client`. The isolation is enforced at multiple levels:

### 1. Database Level

All tenant-scoped models inherit from `ClientScopedModel`:

```python
class ClientScopedModel(models.Model):
    client = models.ForeignKey("core.Client", on_delete=models.CASCADE)

    objects = ClientScopedManager()

    class Meta:
        abstract = True
```

### 2. Query Level

`ClientScopedManager` automatically filters by `request.client`:

```python
class ClientScopedManager(models.Manager):
    def get_queryset(self):
        # Filters by current client from request context
        ...
```

### 3. Middleware Level

`ClientMiddleware` attaches `request.client` based on:
- Subdomain (client.consult.io)
- Header (X-Client-ID for API calls)
- User's assigned client (for dashboard)

### 4. Permission Level

Role-based access within a client:
- **Owner**: Full access, can manage users
- **Staff**: Read/write messages and jobs
- **ReadOnly**: View only

## Data Flow: Inbound Message

1. **Intake**: Form/SMS/voicemail → Worker → `Submission` row
2. **Processing**: Django task polls unprocessed submissions
3. **Contact Matching**: Lookup or create `Contact` by email/phone
4. **Message Creation**: Create `Message` linked to contact
5. **AI Classification**: BAML classifies intent, urgency, category
6. **Dashboard**: Message appears in inbox, sorted by urgency

## Data Flow: Outbound Reply

1. **Staff Action**: Click "Reply" on message in dashboard
2. **Channel Detection**: System knows original channel (email/SMS)
3. **Send**: Mailgun (email) or Twilio (SMS)
4. **Record**: Create outbound `Message` record
5. **Status Update**: Original message marked as replied

## Key Models

```
Client (tenant)
├── User (staff members)
├── Contact (customers)
│   └── Message (inbound/outbound communications)
├── Submission (raw intake, pre-processing)
├── Job (scheduled work)
└── Integration (OAuth connections to Jobber, etc.)
```

## Security Considerations

### Tenant Isolation

- All queries go through `ClientScopedManager`
- Middleware validates client access on every request
- Tests verify cross-tenant data is inaccessible

### Secrets Management

- All secrets in Doppler, never in code or .env files
- Environment-specific secrets (staging vs production)
- Rotation without code changes

### Authentication

- Django's auth with custom User model
- Sessions for dashboard
- API keys for worker-to-Django communication

## Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Backend | Django | Mature, batteries-included, excellent admin |
| Database | Neon Postgres | Serverless, branching, familiar |
| Static Sites | Astro | Fast, flexible, good DX |
| CMS | Sanity | Headless, structured content, good API |
| Edge Logic | Cloudflare Workers | Fast, cheap, global |
| AI | BAML | Typed prompts, testable classification |
| Secrets | Doppler | Centralized, environment-aware |

## Deployment

### Staging

- Auto-deploy on push to main
- Uses staging Doppler config
- Separate Neon branch

### Production

- Manual trigger only
- Requires approval
- Uses production Doppler config

## Future Considerations

- **Horizontal scaling**: Django behind load balancer, Celery workers
- **Read replicas**: For analytics/reporting queries
- **Multi-region**: If latency becomes an issue
- **Billing**: Stripe integration for client subscriptions
