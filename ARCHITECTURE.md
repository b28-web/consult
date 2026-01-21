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

## Interface Contracts

This section defines the API boundaries between system components.

### 1. Astro Sites → Workers (Form Submission)

Sites POST form data to intake workers.

```
POST /intake/{client_slug}/form
Content-Type: application/json

{
  "name": "string",
  "email": "string",
  "phone": "string?",
  "service": "string?",
  "message": "string",
  "source_url": "string",
  "utm_source": "string?",
  "utm_medium": "string?",
  "utm_campaign": "string?"
}

Response: 202 Accepted
{
  "submission_id": "uuid",
  "message": "Thank you, we'll be in touch soon."
}
```

### 2. Workers → Database (Submission Insert)

Workers write raw submissions to Postgres via Neon HTTP API.

```sql
INSERT INTO submissions (
  id, client_id, channel, payload, source_url,
  created_at, processed_at
) VALUES (
  $1, $2, 'form', $3::jsonb, $4, NOW(), NULL
);
```

### 3. Django Dashboard → HTMX Partials

Dashboard uses HTMX for interactivity. Endpoints return HTML fragments.

```
# Inbox message list (with filters)
GET /dashboard/inbox/
GET /dashboard/inbox/?status=unread&urgency=high

# Single message detail
GET /dashboard/inbox/{message_id}/

# Reply to message
POST /dashboard/inbox/{message_id}/reply/
Content-Type: application/x-www-form-urlencoded
body=...&channel=email

# Mark message read/archived
POST /dashboard/inbox/{message_id}/mark/
status=read|archived

# Contact list with search
GET /dashboard/contacts/?q=search

# Contact detail
GET /dashboard/contacts/{contact_id}/
```

### 4. External Webhooks → Workers

Twilio and integration webhooks hit workers.

```
# Twilio SMS
POST /intake/{client_slug}/sms
Content-Type: application/x-www-form-urlencoded
(Twilio standard webhook format)

# Twilio Voice (voicemail)
POST /intake/{client_slug}/voice
(Twilio standard webhook format)

# Cal.com booking
POST /webhooks/calcom
(Cal.com webhook payload)

# Jobber sync
POST /webhooks/jobber
(Jobber webhook payload)
```

### 5. Django → AI Classification (BAML)

Django calls BAML for message classification.

```python
# Input
class MessageInput:
    content: str
    channel: Literal["form", "sms", "voicemail", "email"]
    contact_history: list[str]  # Previous messages for context

# Output
class MessageClassification:
    category: MessageCategory  # inquiry, booking, complaint, spam, etc.
    intent: MessageIntent      # get_quote, schedule, feedback, etc.
    urgency: Literal["low", "medium", "high", "urgent"]
    suggested_action: SuggestedAction
    confidence: float
```

### 6. Site Configuration Interface

Each site reads config from a standard structure:

```typescript
// sites/{client}/src/config.ts
export const siteConfig = {
  client: {
    slug: "coffee-shop",
    name: "The Daily Grind",
    phone: "(555) 123-4567",
    email: "hello@dailygrind.com",
    address: "123 Main St, Austin, TX 78701",
  },
  intake: {
    formUrl: "https://intake.consult.io/coffee-shop/form",
  },
  services: [
    { name: "Coffee Bar", slug: "coffee", description: "..." },
    { name: "Catering", slug: "catering", description: "..." },
  ],
  social: {
    instagram: "https://instagram.com/...",
    facebook: "https://facebook.com/...",
  },
  theme: {
    // CSS custom properties override defaults
    "--client-primary-500": "oklch(0.45 0.12 30)", // Coffee brown
  },
};
```

## Directory Structure (Detailed)

```
/
├── apps/
│   └── web/                      # Django application
│       ├── config/               # Django settings, URLs, WSGI
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── wsgi.py
│       ├── core/                 # Multi-tenancy foundation
│       │   ├── models.py         # Client, User, ClientScopedModel
│       │   ├── middleware.py     # ClientMiddleware
│       │   └── managers.py       # ClientScopedManager
│       ├── inbox/                # Message handling
│       │   ├── models.py         # Contact, Message, Submission
│       │   ├── views.py          # HTMX views for inbox
│       │   ├── tasks.py          # Submission processing
│       │   └── templates/inbox/  # HTMX partials
│       ├── crm/                  # CRM features
│       │   ├── models.py         # Job, Note, Tag
│       │   └── views.py
│       └── manage.py
│
├── sites/                        # Astro static sites
│   ├── _template/                # Base template for new sites
│   │   ├── astro.config.mjs
│   │   ├── package.json
│   │   ├── tailwind.config.ts
│   │   └── src/
│   │       ├── config.ts         # Site-specific config
│   │       ├── layouts/
│   │       ├── pages/
│   │       └── components/
│   ├── coffee-shop/
│   ├── hauler/                   # Has Cal.com embed
│   ├── cleaning/
│   ├── landscaper/
│   ├── barber/
│   ├── data-analytics/
│   ├── web-dev/
│   └── local-agency/
│
├── workers/                      # Cloudflare Workers
│   ├── intake/                   # Form/SMS/voice intake
│   │   ├── src/index.ts
│   │   ├── wrangler.toml
│   │   └── package.json
│   └── webhooks/                 # External integrations
│       ├── src/index.ts
│       └── wrangler.toml
│
├── packages/
│   ├── schemas/                  # Shared Pydantic/TS schemas
│   └── shared-ui/                # Tailwind preset, base styles
│
├── baml_src/                     # AI classification schemas
└── scripts/                      # Dev utilities
    └── new-site.sh               # Scaffold new client site
```

## Future Considerations

- **Horizontal scaling**: Django behind load balancer, Celery workers
- **Read replicas**: For analytics/reporting queries
- **Multi-region**: If latency becomes an issue
- **Billing**: Stripe integration for client subscriptions
