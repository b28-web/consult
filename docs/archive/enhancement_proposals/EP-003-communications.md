# EP-003: Communications (Twilio + Resend)

**Status:** completed
**Last Updated:** 2026-01-22

## Goal

Enable two-way communication: receive SMS/voicemail via Twilio webhooks, send replies via Twilio SMS and Resend email. Complete the communication loop.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 003-A | Twilio SMS webhook handling | ✓ |
| 003-B | Twilio voicemail handling | ✓ |
| 003-C | Twilio signature validation | ✓ |
| 003-D | Outbound SMS via Twilio | ✓ |
| 003-E | Outbound email via Resend | ✓ |
| 003-F | Reply channel selection logic | ✓ |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SMS provider | Twilio | Industry standard, good API |
| Email provider | Resend | Modern API, great DX, React Email support |
| Webhook receiver | Cloudflare Worker | Fast, validates before DB write |
| Phone numbers | Per-client Twilio numbers | Proper caller ID, client isolation |

## Dependencies

- [x] EP-001 complete (intake worker deployed)
- [x] EP-002 complete (submission processing works)
- [x] Twilio account with phone numbers provisioned
- [x] Resend domain verified
- [x] Doppler secrets: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, RESEND_API_KEY

## Architecture Notes

```
Inbound SMS/Voice:
Twilio → Worker (validates signature) → Submission table → Processing → Message

Outbound:
Dashboard Reply → Django → Twilio API (SMS) or Resend API (email) → Customer
```

Phone number mapping:
- Each Client has a Twilio phone number stored in `Client.twilio_phone`
- Inbound webhooks include the "To" number to identify the client
- Outbound uses the client's number as the sender

## Progress Log

### 2026-01-22
- **003-F Complete**: Reply channel selection logic
  - `get_reply_channels()` helper with smart defaults
  - SMS/voicemail → SMS, form/email → email
  - Falls back to available channel if default unavailable
  - Dynamic channel dropdown in reply form
  - 7 new tests, all 63 inbox tests pass

- **003-E Complete**: Outbound email via Resend
  - `send_email()` with from address using client slug
  - In-Reply-To header support for threading
  - Reply view handles email channel
  - 7 new tests, 56 total pass

- **003-D Complete**: Outbound SMS via Twilio
  - Added `twilio_phone` to Client, `external_id` to Message
  - Created `send_sms()` service with error handling
  - Reply view sends SMS when channel=sms
  - 6 new tests, 49 total pass

- **003-C Complete**: Twilio signature validation
  - Web Crypto API for HMAC-SHA1 (Cloudflare Workers compatible)
  - All Twilio webhooks validated, 403 on failure
  - Graceful skip in dev mode (no auth token)

- **003-B Complete**: Voicemail handling implemented
  - Multi-phase flow: `/voice` → `/voice-complete` → `/voice-transcription`
  - Worker creates submission on recording complete, updates with transcription
  - Django extracts transcription as body, recording URL as fallback
  - 3 new tests, all 43 inbox tests pass

- **003-A Complete**: SMS webhook handling implemented
  - Worker extracts From, To, Body, MessageSid, MMS media URLs
  - Django processes SMS with `from` as phone
  - 3 new tests added, all 40 inbox tests pass

### 2026-01-21
- EP created
- Intake worker already handles SMS/voice routes (stubs)
- Next: depends on EP-001 and EP-002
