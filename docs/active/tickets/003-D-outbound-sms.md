# 003-D: Outbound SMS via Twilio

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Send SMS replies from the dashboard using Twilio API.

## Acceptance Criteria

- [ ] Django service/utility for sending SMS
- [ ] Uses client's Twilio phone as sender
- [ ] Recipient is contact's phone number
- [ ] Creates outbound Message record
- [ ] Handles Twilio API errors gracefully
- [ ] Dashboard reply form triggers send when channel=sms

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

(Not started)
