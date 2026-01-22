# 003-A: Twilio SMS Webhook Handling

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Properly handle inbound SMS from Twilio, extracting message content and sender info.

## Acceptance Criteria

- [x] Worker extracts: From (phone), Body (message), To (our number)
- [x] Maps "To" number to client_slug via lookup or pattern
- [x] Creates submission with channel="sms", proper payload
- [x] Returns valid TwiML response (empty = no auto-reply)
- [x] Handles MMS (media URLs stored in payload)

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

### 2026-01-22
- Implemented SMS content extraction in worker (`workers/intake/src/index.ts`)
  - Extracts From, To, Body, MessageSid from Twilio webhook
  - Handles MMS with media_urls array (MediaUrl0, MediaUrl1, etc.)
  - Returns empty TwiML response (no auto-reply)
- Updated Django processing (`apps/web/inbox/management/commands/process_submissions.py`)
  - SMS channel uses `from` field for phone (not `phone`)
  - SMS channel uses `body` directly (not `message`)
- Added tests for SMS processing (3 new tests)
- All 40 inbox tests pass
