# 003-C: Twilio Signature Validation

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Validate Twilio webhook signatures to prevent spoofed requests.

## Acceptance Criteria

- [ ] X-Twilio-Signature header validated on all Twilio webhooks
- [ ] Invalid signatures rejected with 403
- [ ] Auth token loaded from Doppler (TWILIO_AUTH_TOKEN)
- [ ] Validation uses request URL + sorted params + auth token
- [ ] Works for both SMS and voice webhooks

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

(Not started)
