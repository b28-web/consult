# 004-B: Cal.com Webhook Handler

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** pending

## Summary

Handle Cal.com booking webhooks to create Job records automatically.

## Acceptance Criteria

- [ ] Worker endpoint: `POST /webhooks/calcom`
- [ ] Validates webhook signature
- [ ] Handles BOOKING_CREATED event
- [ ] Handles BOOKING_CANCELLED event
- [ ] Creates/updates Job record via submission queue
- [ ] Maps Cal.com attendee to Contact

## Implementation Notes

Cal.com webhook payload:
```json
{
  "triggerEvent": "BOOKING_CREATED",
  "payload": {
    "uid": "booking-uid",
    "title": "30 Min Meeting",
    "startTime": "2026-01-25T10:00:00Z",
    "endTime": "2026-01-25T10:30:00Z",
    "attendees": [{
      "email": "customer@example.com",
      "name": "John Doe",
      "timeZone": "America/Chicago"
    }],
    "organizer": {
      "email": "business@example.com"
    }
  }
}
```

Webhook signature validation:
```typescript
const signature = request.headers.get('X-Cal-Signature-256');
const payload = await request.text();
const expected = crypto.createHmac('sha256', webhookSecret)
  .update(payload)
  .digest('hex');
```

Create submission with channel="calcom":
```json
{
  "event_type": "BOOKING_CREATED",
  "booking_uid": "...",
  "title": "...",
  "start_time": "...",
  "attendee_name": "...",
  "attendee_email": "..."
}
```

Processing creates:
1. Contact (find/create by email)
2. Job with calcom_event_id set

## Progress

(Not started)
