# 003-C: Twilio Signature Validation

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Validate Twilio webhook signatures to prevent spoofed requests.

## Acceptance Criteria

- [x] X-Twilio-Signature header validated on all Twilio webhooks
- [x] Invalid signatures rejected with 403
- [x] Auth token loaded from Doppler (TWILIO_AUTH_TOKEN)
- [x] Validation uses request URL + sorted params + auth token
- [x] Works for both SMS and voice webhooks

## Implementation Notes

Twilio signature validation in Worker:

```typescript
import { createHmac } from 'node:crypto';

function validateTwilioSignature(
  authToken: string,
  signature: string,
  url: string,
  params: Record<string, string>
): boolean {
  // Sort params alphabetically and concatenate
  const data = url + Object.keys(params)
    .sort()
    .map(key => key + params[key])
    .join('');

  const expected = createHmac('sha1', authToken)
    .update(data)
    .digest('base64');

  return signature === expected;
}
```

Note: Cloudflare Workers don't have Node crypto by default. Use Web Crypto API:
```typescript
const encoder = new TextEncoder();
const key = await crypto.subtle.importKey(
  'raw',
  encoder.encode(authToken),
  { name: 'HMAC', hash: 'SHA-1' },
  false,
  ['sign']
);
const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(data));
```

## Progress

### 2026-01-22
- Implemented `validateTwilioSignature()` using Web Crypto API (HMAC-SHA1)
- Added `requireTwilioSignature()` helper that returns 403 on failure
- Integrated validation into main router for all Twilio channels (sms, voice, voice-complete, voice-transcription)
- Refactored handlers to receive pre-parsed FormData (read once for validation and handler)
- Graceful degradation: skips validation if TWILIO_AUTH_TOKEN not set (dev mode)
- TypeScript compiles without errors
