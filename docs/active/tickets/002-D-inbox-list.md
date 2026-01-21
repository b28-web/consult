# 002-D: Inbox List View (HTMX)

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Build the inbox list view showing all messages, with filters and real-time updates via HTMX.

## Acceptance Criteria

- [ ] `/dashboard/inbox/` shows message list
- [ ] Messages sorted by urgency (high first), then date
- [ ] Each row shows: contact name, preview, channel icon, urgency badge, time
- [ ] Filter by status (unread, read, replied, archived)
- [ ] Filter by channel (form, sms, voicemail, email)
- [ ] Filter by urgency
- [ ] Clicking row loads detail in side panel (HTMX)
- [ ] Unread count in sidebar updates on changes

## Implementation Notes

```
apps/web/inbox/templates/inbox/
├── inbox.html              # Full page (extends dashboard/base.html)
├── partials/
│   ├── message_list.html   # Just the list (HTMX target)
│   ├── message_row.html    # Single row
│   └── filters.html        # Filter controls
```

HTMX patterns:
```html
<!-- Filter triggers list reload -->
<select hx-get="/dashboard/inbox/" hx-target="#message-list" name="status">
  <option value="">All</option>
  <option value="unread">Unread</option>
</select>

<!-- Row click loads detail -->
<div hx-get="/dashboard/inbox/{{ id }}/" hx-target="#detail-panel">
```

## Progress

(Not started)
