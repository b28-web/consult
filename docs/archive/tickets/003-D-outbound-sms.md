# 003-D: Outbound SMS via Twilio

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Send SMS replies from the dashboard using Twilio API.

## Acceptance Criteria

- [x] Django service/utility for sending SMS
- [x] Uses client's Twilio phone as sender
- [x] Recipient is contact's phone number
- [x] Creates outbound Message record
- [x] Handles Twilio API errors gracefully
- [x] Dashboard reply form triggers send when channel=sms

## Implementation Notes

```python
# apps/web/inbox/services.py
from twilio.rest import Client

def send_sms(client: Client, to_phone: str, body: str) -> str:
    """Send SMS via Twilio. Returns message SID."""
    twilio = TwilioClient(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    message = twilio.messages.create(
        body=body,
        from_=client.twilio_phone,
        to=to_phone
    )

    return message.sid
```

Add to Client model:
```python
class Client(models.Model):
    # ...
    twilio_phone = models.CharField(max_length=20, blank=True)
```

In reply view:
```python
def message_reply(request, message_id):
    # ...
    if channel == 'sms':
        sid = send_sms(request.client, contact.phone, body)
        # Store SID in outbound message for tracking
```

## Progress

### 2026-01-22
- Added `twilio_phone` field to Client model (migration 0003)
- Added `external_id` field to Message model for Twilio SID (migration 0003)
- Created `apps/web/inbox/services.py` with `send_sms()` function
- Added Twilio settings to Django settings (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`)
- Updated `message_reply` view to send SMS when channel=sms
- Added Twilio SDK dependency
- 6 new tests for SMS service, all 49 inbox tests pass
