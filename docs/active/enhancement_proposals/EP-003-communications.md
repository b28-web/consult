# EP-003: Communications (Twilio + Mailgun)

**Status:** planned
**Last Updated:** 2026-01-21

## Goal

Enable two-way communication: receive SMS/voicemail via Twilio webhooks, send replies via Twilio SMS and Resend email. Complete the communication loop.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 003-A | Twilio SMS webhook handling | pending |
| 003-B | Twilio voicemail handling | pending |
| 003-C | Twilio signature validation | pending |
| 003-D | Outbound SMS via Twilio | pending |
| 003-E | Outbound email via Resend | pending |
| 003-F | Reply channel selection logic | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SMS provider | Twilio | Industry standard, good API |
| Email provider | Resend | Modern API, great DX, React Email support |
| Webhook receiver | Cloudflare Worker | Fast, validates before DB write |
| Phone numbers | Per-client Twilio numbers | Proper caller ID, client isolation |

## Dependencies

- [x] EP-001 complete (intake worker deployed)
- [ ] EP-002 complete (submission processing works)
- [ ] Twilio account with phone numbers provisioned
- [ ] Mailgun domain verified
- [ ] Doppler secrets: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, RESEND_API_KEY

## Architecture Notes

```
Inbound SMS/Voice:
Twilio → Worker (validates signature) → Submission table → Processing → Message

Outbound:
Dashboard Reply → Django → Twilio API (SMS) or Mailgun API (email) → Customer
```

Phone number mapping:
- Each Client has a Twilio phone number stored in `Client.twilio_phone`
- Inbound webhooks include the "To" number to identify the client
- Outbound uses the client's number as the sender

## Progress Log

### 2026-01-21
- EP created
- Intake worker already handles SMS/voice routes (stubs)
- Next: depends on EP-001 and EP-002
