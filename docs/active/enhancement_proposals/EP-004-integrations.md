# EP-004: External Integrations (Cal.com + Jobber)

**Status:** planned
**Last Updated:** 2026-01-21

## Goal

Connect to external scheduling and CRM tools. Cal.com for appointment booking, Jobber for job management sync. Enables clients who already use these tools.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 004-A | Cal.com embed component | pending |
| 004-B | Cal.com webhook handler | pending |
| 004-C | Jobber OAuth integration | pending |
| 004-D | Jobber webhook sync | pending |
| 004-E | Integration settings UI | pending |

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

### 2026-01-21
- EP created
- Job model already exists in crm app
- Next: depends on EP-001, EP-002
