# EP-004: External Integrations (Cal.com + Jobber)

**Status:** complete
**Last Updated:** 2026-01-22

## Goal

Connect to external scheduling and CRM tools. Cal.com for appointment booking, Jobber for job management sync. Enables clients who already use these tools.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 004-A | Cal.com embed component | ✓ |
| 004-B | Cal.com webhook handler | ✓ |
| 004-C | Jobber OAuth integration | ✓ |
| 004-D | Jobber webhook sync | ✓ |
| 004-E | Integration settings UI | ✓ |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cal.com integration | Embed + webhooks | Embed for booking, webhooks for sync |
| Jobber integration | OAuth + webhooks | Full API access, real-time sync |
| Webhook receiver | Cloudflare Worker | Consistent with other webhooks |
| Credentials storage | Per-client in DB | Multi-tenant, encrypted |

## Dependencies

- [ ] EP-001 complete
- [ ] EP-002 complete (Jobs model exists)
- [ ] Cal.com account with API access
- [ ] Jobber partner API access

## Architecture Notes

```
Cal.com Flow:
Site embed → Cal.com hosted booking → Webhook → Worker → Submission → Job record

Jobber Flow:
OAuth dance → Store tokens → Webhooks for updates → Sync Job records
```

Integration model:
```python
class Integration(ClientScopedModel):
    provider = models.CharField(max_length=50)  # calcom, jobber
    credentials = models.JSONField()  # Encrypted OAuth tokens
    webhook_secret = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
```

## Progress Log

### 2026-01-22
- **EP-004 COMPLETE** - All tickets finished
- **004-D complete**: Jobber webhook sync
  - Worker endpoint: `POST /webhooks/jobber/{client_slug}`
  - HMAC-SHA256 signature validation
  - Handles job and client events
  - Django processor for Job + Contact creation/update
- **004-C + 004-E complete**: Jobber OAuth + Integration Settings UI
  - Created `integrations` Django app with `Integration` model
  - Full OAuth flow: authorize, callback, disconnect
  - Token refresh mechanism with expiry checking
  - Dashboard settings page at `/dashboard/settings/`
  - Connect/disconnect buttons for Jobber
- **004-B complete**: Cal.com webhook handler implemented
  - Worker endpoint: `POST /webhooks/calcom/{client_slug}`
  - HMAC-SHA256 signature validation
  - Handles BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED
  - Django processor creates Contact + Job records
- **004-A complete**: CalEmbed.astro component created
  - Supports inline/popup modes, brand colors, layout options
  - Integrated into contact page template
  - Synced to coffee-shop site

### 2026-01-21
- EP created
- Job model already exists in crm app
- Next: depends on EP-001, EP-002
