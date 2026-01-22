# 004-E: Integration Settings UI

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** complete

## Summary

Dashboard UI for managing external integrations (connect, disconnect, status).

## Acceptance Criteria

- [x] `/dashboard/settings/` page (simplified path)
- [x] Shows available integrations (Cal.com, Jobber)
- [x] Shows connection status for each
- [x] Connect button initiates OAuth flow
- [x] Disconnect button revokes and removes tokens
- [ ] Shows last sync time and any errors (deferred - requires webhook sync)

## Implementation Notes

```
apps/web/integrations/
├── __init__.py
├── apps.py
├── models.py          # Integration model
├── views.py           # OAuth flows, settings page
├── urls.py
└── templates/integrations/
    ├── settings.html          # Main settings page
    └── partials/
        ├── integration_card.html   # Single integration status
        └── connect_button.html
```

Integration card shows:
- Provider logo/name
- Status: Connected / Not connected
- If connected: account name, last sync
- Connect or Disconnect button

HTMX for connecting:
```html
<button
  hx-get="/dashboard/settings/integrations/jobber/authorize/"
  hx-target="body"
  class="btn btn-primary"
>
  Connect Jobber
</button>
```

After OAuth success, redirect back to settings with success message.

## Progress

### 2026-01-22
- Created `/dashboard/settings/` page with integrations section
- Integration cards for Jobber and Cal.com with:
  - Provider logo and description
  - Connection status indicator
  - Connect/Disconnect buttons
- Added Settings link to dashboard sidebar navigation
- Note: Last sync time deferred to 004-D when webhook sync is implemented
