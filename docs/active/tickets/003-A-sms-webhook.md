# 003-A: Twilio SMS Webhook Handling

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Properly handle inbound SMS from Twilio, extracting message content and sender info.

## Acceptance Criteria

- [ ] Worker extracts: From (phone), Body (message), To (our number)
- [ ] Maps "To" number to client_slug via lookup or pattern
- [ ] Creates submission with channel="sms", proper payload
- [ ] Returns valid TwiML response (empty = no auto-reply)
- [ ] Handles MMS (media URLs stored in payload)

## Implementation Notes

Twilio webhook payload (form-urlencoded):
```
From: +15551234567
To: +15559876543
Body: "Hi, I need a quote for lawn service"
NumMedia: 0
MessageSid: SMxxxxxxxx
```

Worker needs to map phone numbers to clients:
```typescript
// Option 1: Environment variable mapping
const CLIENT_PHONES: Record<string, string> = {
  "+15559876543": "landscaper",
  "+15558765432": "coffee-shop",
};

// Option 2: Database lookup (slower but dynamic)
// Query clients table by twilio_phone
```

Payload to store:
```json
{
  "from": "+15551234567",
  "to": "+15559876543",
  "body": "Hi, I need a quote...",
  "message_sid": "SMxxxxxxxx",
  "media_urls": []
}
```

## Progress

(Not started)
