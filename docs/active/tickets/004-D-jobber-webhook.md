# 004-D: Jobber Webhook Sync

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** pending

## Summary

Handle Jobber webhooks to keep Job records in sync.

## Acceptance Criteria

- [ ] Worker endpoint: `POST /webhooks/jobber`
- [ ] Validates webhook signature
- [ ] Handles job.created, job.updated, job.completed events
- [ ] Handles client.created (Jobber's client = our Contact)
- [ ] Creates/updates Job and Contact records
- [ ] Bi-directional: changes in dashboard can push to Jobber (future)

## Implementation Notes

Jobber webhook payload:
```json
{
  "event": "job.created",
  "data": {
    "id": "123",
    "title": "Lawn Service",
    "status": "scheduled",
    "scheduled_at": "2026-01-25T10:00:00Z",
    "client": {
      "id": "456",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "555-1234"
    },
    "address": {
      "street": "123 Main St",
      "city": "Austin",
      "state": "TX"
    }
  }
}
```

Processing creates submission with channel="jobber":
```json
{
  "event": "job.created",
  "jobber_job_id": "123",
  "title": "Lawn Service",
  "status": "scheduled",
  "scheduled_at": "...",
  "client_name": "John Doe",
  "client_email": "...",
  "client_phone": "...",
  "address": "..."
}
```

Map Jobber status to our Job.Status:
- requires_invoicing → completed
- scheduled → scheduled
- in_progress → in_progress

## Progress

(Not started)
