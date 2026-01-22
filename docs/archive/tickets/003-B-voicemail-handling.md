# 003-B: Twilio Voicemail Handling

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Handle voice calls that go to voicemail, storing the recording and transcription.

## Acceptance Criteria

- [x] Worker returns TwiML to prompt for voicemail
- [x] Recording callback stores audio URL in submission
- [x] Transcription (Twilio's) stored when available
- [x] Submission created with channel="voicemail"
- [x] Processing extracts transcription as message body

## Implementation Notes

Two-phase webhook:

**Phase 1: Initial call (voice webhook)**
```xml
<Response>
  <Say>Please leave a message after the beep.</Say>
  <Record maxLength="120" transcribe="true"
          action="/intake/{client}/voice-complete"
          transcribeCallback="/intake/{client}/voice-transcription" />
</Response>
```

**Phase 2: Recording complete callback**
```
RecordingUrl: https://api.twilio.com/2010-04-01/Accounts/.../Recordings/RExx
RecordingDuration: 45
From: +15551234567
```

**Phase 3: Transcription callback (async)**
```
TranscriptionText: "Hi, I need someone to pick up a couch..."
TranscriptionStatus: completed
RecordingSid: RExx
```

May need two submissions or update pattern for transcription arriving later.

## Progress

### 2026-01-22
- Implemented multi-phase voicemail webhook flow in worker:
  - `/voice` - Returns TwiML with callbacks (no submission yet)
  - `/voice-complete` - Creates submission with recording URL
  - `/voice-transcription` - Updates submission payload with transcription
- Added `VoicemailPayload` interface for structured data
- Updated Django processing:
  - Voicemail extracts phone from `from` field
  - Uses `transcription_text` as body, falls back to recording URL placeholder
- Transcription callback also updates already-processed messages
- Added 3 new tests for voicemail processing
- All 43 inbox tests pass
