# 003-B: Twilio Voicemail Handling

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Handle voice calls that go to voicemail, storing the recording and transcription.

## Acceptance Criteria

- [ ] Worker returns TwiML to prompt for voicemail
- [ ] Recording callback stores audio URL in submission
- [ ] Transcription (Twilio's) stored when available
- [ ] Submission created with channel="voicemail"
- [ ] Processing extracts transcription as message body

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

(Not started)
