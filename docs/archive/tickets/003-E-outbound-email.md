# 003-E: Outbound Email via Resend

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Send email replies from the dashboard using Resend API.

## Acceptance Criteria

- [x] Django service/utility for sending email
- [x] Uses client's email domain (e.g., reply@clientname.consult.io)
- [x] Recipient is contact's email address
- [x] Creates outbound Message record
- [x] Handles Resend API errors gracefully
- [x] Dashboard reply form triggers send when channel=email

## Implementation Notes

```python
# apps/web/inbox/services.py
import resend

resend.api_key = settings.RESEND_API_KEY

def send_email(client: Client, to_email: str, subject: str, body: str) -> str:
    """Send email via Resend. Returns email ID."""
    response = resend.Emails.send({
        "from": f"{client.name} <reply@{client.slug}.consult.io>",
        "to": to_email,
        "subject": subject,
        "text": body,
    })
    return response["id"]
```

Add `resend` to dependencies:
```bash
uv add resend
```

Email threading:
- Store original message's email Message-ID
- Set `headers.In-Reply-To` on replies for threading

```python
resend.Emails.send({
    "from": f"{client.name} <reply@{client.slug}.consult.io>",
    "to": to_email,
    "subject": f"Re: {original_subject}",
    "text": body,
    "headers": {
        "In-Reply-To": original_message_id,
    }
})
```

## Progress

### 2026-01-22
- Added Resend SDK dependency
- Created `send_email()` function in services.py with threading support
- Added `RESEND_API_KEY` to Django settings
- Updated `message_reply` view to handle email channel
- Builds reply subject with "Re:" prefix
- 7 new tests for email service, all 56 inbox tests pass
