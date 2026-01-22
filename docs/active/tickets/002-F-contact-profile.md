# 002-F: Contact Profile View

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Build the contact profile view showing all information about a customer.

## Acceptance Criteria

- [x] `/dashboard/contacts/` shows searchable contact list
- [x] `/dashboard/contacts/{id}/` shows contact detail
- [x] Profile shows: name, email, phone, address, tags
- [x] Shows all messages (inbound and outbound)
- [x] Shows all jobs linked to contact
- [x] Notes section (add/view internal notes)
- [x] Edit contact info inline

## Implementation Notes

```
apps/web/crm/templates/crm/
├── contact_list.html
├── contact_detail.html
└── partials/
    ├── contact_row.html
    ├── contact_messages.html
    ├── contact_jobs.html
    └── contact_notes.html
```

Search with HTMX:
```html
<input type="search"
       hx-get="/dashboard/contacts/"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#contact-list"
       name="q"
       placeholder="Search contacts...">
```

## Progress

### 2026-01-22
- Created CRM template structure:
  - `contact_list.html` - Full page with search input
  - `contact_detail.html` - Full page with 3-column layout
  - Partials: contact_row, contact_list_items, contact_info, contact_edit_form
  - Partials: contact_messages, contact_jobs, contact_notes, note_item
- Updated CRM views:
  - Added `@login_required` to all views
  - `contact_list` returns full page or HTMX partial
  - `contact_detail` with prefetch for messages, jobs, notes, tags
  - `contact_edit` GET/POST for inline editing
  - `contact_info` for cancel button
  - `add_note` POST endpoint
- Added URL routes for new endpoints
- Tests: 17 new tests for CRM views (63 total)
- All quality checks pass
