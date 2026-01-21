# 003-E: Outbound Email via Resend

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Send email replies from the dashboard using Resend API.

## Acceptance Criteria

- [ ] Django service/utility for sending email
- [ ] Uses client's email domain (e.g., reply@clientname.consult.io)
- [ ] Recipient is contact's email address
- [ ] Creates outbound Message record
- [ ] Handles Resend API errors gracefully
- [ ] Dashboard reply form triggers send when channel=email

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

(Not started)
