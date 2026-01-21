# 002-F: Contact Profile View

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Build the contact profile view showing all information about a customer.

## Acceptance Criteria

- [ ] `/dashboard/contacts/` shows searchable contact list
- [ ] `/dashboard/contacts/{id}/` shows contact detail
- [ ] Profile shows: name, email, phone, address, tags
- [ ] Shows all messages (inbound and outbound)
- [ ] Shows all jobs linked to contact
- [ ] Notes section (add/view internal notes)
- [ ] Edit contact info inline

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

(Not started)
