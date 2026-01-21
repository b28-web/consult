# 002-C: Dashboard Shell with Auth

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Create the dashboard layout shell with authentication. This is the container for inbox, contacts, jobs views.

## Acceptance Criteria

- [ ] Login page at `/dashboard/login/`
- [ ] Logout functionality
- [ ] Dashboard requires authentication (redirect to login)
- [ ] Base template with sidebar navigation
- [ ] DaisyUI styling (drawer layout for mobile)
- [ ] Current user and client displayed
- [ ] HTMX loaded in base template

## Implementation Notes

```
apps/web/dashboard/
├── __init__.py
├── apps.py
├── views.py          # Login, logout, dashboard home
├── urls.py
└── templates/dashboard/
    ├── base.html     # Shell with sidebar, HTMX
    ├── login.html
    └── home.html     # Landing after login
```

Sidebar navigation:
- Inbox (unread count badge)
- Contacts
- Jobs
- Settings (future)

Use DaisyUI drawer component for responsive sidebar.

## Progress

(Not started)
