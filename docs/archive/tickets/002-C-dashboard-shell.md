# 002-C: Dashboard Shell with Auth

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Create the dashboard layout shell with authentication. This is the container for inbox, contacts, jobs views.

## Acceptance Criteria

- [x] Login page at `/dashboard/login/`
- [x] Logout functionality
- [x] Dashboard requires authentication (redirect to login)
- [x] Base template with sidebar navigation
- [x] DaisyUI styling (drawer layout for mobile)
- [x] Current user and client displayed
- [x] HTMX loaded in base template

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

### 2026-01-22

Implemented dashboard shell with authentication:

**Files created:**
- `apps/web/dashboard/__init__.py`
- `apps/web/dashboard/apps.py` - DashboardConfig
- `apps/web/dashboard/views.py` - login_view, logout_view, home
- `apps/web/dashboard/urls.py` - URL routing
- `apps/web/dashboard/templates/dashboard/base.html` - Shell with DaisyUI sidebar
- `apps/web/dashboard/templates/dashboard/login.html` - Login page
- `apps/web/dashboard/templates/dashboard/home.html` - Dashboard home
- `apps/web/dashboard/tests/__init__.py`
- `apps/web/dashboard/tests/test_views.py` - 9 tests

**Files modified:**
- `apps/web/config/settings.py` - Added dashboard to INSTALLED_APPS, LOGIN_URL settings
- `apps/web/config/urls.py` - Added dashboard URLs
- `apps/web/core/middleware.py` - Updated to allow unauthenticated access to login/logout

**Features:**
- Login page at `/dashboard/login/`
- Logout via `/dashboard/logout/`
- Dashboard home at `/dashboard/`
- DaisyUI drawer layout with responsive sidebar
- Sidebar shows: Home, Inbox (with unread badge), Contacts, Jobs (coming soon)
- User info displayed in sidebar footer
- HTMX loaded in base template
- Alpine.js loaded for interactivity
- CSRF token auto-included via HTMX headers

**Authentication flow:**
1. Anonymous users accessing `/dashboard/` redirected to login
2. Login accepts username/password
3. Successful login redirects to home (or `next` URL)
4. Invalid credentials show error message
5. Logout redirects to login page

**Tests (9 passing):**
- test_login_page_renders
- test_login_redirects_authenticated_user
- test_login_with_valid_credentials
- test_login_with_invalid_credentials
- test_login_respects_next_parameter
- test_logout_logs_out_user
- test_home_requires_authentication
- test_home_renders_for_authenticated_user
- test_home_shows_user_info

**Quality:**
- All ruff checks pass
- All mypy checks pass
- All 9 tests pass
