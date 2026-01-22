# 002-E: Message Detail Panel (HTMX)

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Build the message detail panel showing full message content, classification, and reply form.

## Acceptance Criteria

- [x] Detail panel loads via HTMX when clicking inbox row
- [x] Shows: full message body, contact info, channel, timestamp
- [x] Shows AI classification: category, intent, urgency, suggested action
- [x] Shows contact history (previous messages from same contact)
- [x] Reply form with channel selector (match original or override)
- [x] Mark as read/archived buttons
- [x] Link to full contact profile

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

### 2026-01-22
- Most functionality already implemented in 002-D
- Added contact history section:
  - Created `contact_history.html` partial showing last 5 messages from contact
  - Updated `message_detail` view to query contact history
  - History shows direction indicator, channel, timestamp, and message preview
  - Clicking history items loads that message in detail panel
- Added contact profile link:
  - Contact name in header now links to CRM contact detail
  - "View full profile" link in contact history section
- Tests: 3 new tests for contact history (46 total)
- All quality checks pass
