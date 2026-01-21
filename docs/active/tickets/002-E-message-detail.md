# 002-E: Message Detail Panel (HTMX)

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Build the message detail panel showing full message content, classification, and reply form.

## Acceptance Criteria

- [ ] Detail panel loads via HTMX when clicking inbox row
- [ ] Shows: full message body, contact info, channel, timestamp
- [ ] Shows AI classification: category, intent, urgency, suggested action
- [ ] Shows contact history (previous messages from same contact)
- [ ] Reply form with channel selector (match original or override)
- [ ] Mark as read/archived buttons
- [ ] Link to full contact profile

## Implementation Notes

```
apps/web/inbox/templates/inbox/partials/
├── message_detail.html     # Full detail panel
├── reply_form.html         # Reply textarea + submit
├── reply_success.html      # Shown after successful reply
└── contact_history.html    # Previous messages snippet
```

Reply form:
```html
<form hx-post="/dashboard/inbox/{{ id }}/reply/" hx-target="#reply-status">
  <textarea name="body" required></textarea>
  <select name="channel">
    <option value="email">Email</option>
    <option value="sms">SMS</option>
  </select>
  <button type="submit">Send Reply</button>
</form>
```

## Progress

(Not started)
