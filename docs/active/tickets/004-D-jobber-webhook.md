# 004-D: Jobber Webhook Sync

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** complete

## Summary

Handle Jobber webhooks to keep Job records in sync.

## Acceptance Criteria

- [x] Worker endpoint: `POST /webhooks/jobber/{client_slug}`
- [x] Validates webhook signature
- [x] Handles job.created, job.updated, job.completed events
- [x] Handles client.created, client.updated (Jobber's client = our Contact)
- [x] Creates/updates Job and Contact records
- [ ] Bi-directional: changes in dashboard can push to Jobber (future - deferred)

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

### 2026-01-22
- Added Jobber webhook route to intake worker: `POST /webhooks/jobber/{client_slug}`
- Implemented HMAC-SHA256 signature validation (X-Jobber-Hmac-SHA256 header)
- Handles job.created, job.updated, job.completed events
- Handles client.created, client.updated events for Contact sync
- Added `_process_jobber_webhook` and `_process_jobber_client` to Django processor
- Maps Jobber status (scheduled/in_progress/requires_invoicing) to Job.Status
- All quality checks pass (ruff, mypy, tsc)
- Note: Bi-directional sync (push to Jobber) deferred to future enhancement
