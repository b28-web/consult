# 002-D: Inbox List View (HTMX)

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Build the inbox list view showing all messages, with filters and real-time updates via HTMX.

## Acceptance Criteria

- [x] `/dashboard/inbox/` shows message list
- [x] Messages sorted by urgency (high first), then date
- [x] Each row shows: contact name, preview, channel icon, urgency badge, time
- [x] Filter by status (unread, read, replied, archived)
- [x] Filter by channel (form, sms, voicemail, email)
- [x] Filter by urgency
- [x] Clicking row loads detail in side panel (HTMX)
- [x] Unread count in sidebar updates on changes

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

### 2026-01-22
- Created template structure:
  - `inbox/inbox.html` - Full page with split panel layout
  - `inbox/partials/message_list.html` - Message list (HTMX target)
  - `inbox/partials/message_row.html` - Single message row
  - `inbox/partials/filters.html` - Status/channel/urgency filters
  - `inbox/partials/message_detail.html` - Detail panel
  - `inbox/partials/reply_success.html` and `reply_error.html` - Reply feedback
- Updated `inbox/views.py`:
  - Added `@login_required` to all views
  - `inbox_list` returns full page or HTMX partial based on request
  - Messages sorted by urgency (urgent→high→medium→low→empty), then by date
  - Filters only inbound messages (excludes outbound replies)
- Added `django.contrib.humanize` to INSTALLED_APPS for naturaltime filter
- Tests: 18 new tests covering:
  - Authentication requirements
  - Multi-tenancy isolation
  - Filtering by status/channel/urgency
  - Urgency-based sorting
  - HTMX partial responses
  - Unread count display
- All 43 tests pass
