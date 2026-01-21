# 004-E: Integration Settings UI

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** pending

## Summary

Dashboard UI for managing external integrations (connect, disconnect, status).

## Acceptance Criteria

- [ ] `/dashboard/settings/integrations/` page
- [ ] Shows available integrations (Cal.com, Jobber)
- [ ] Shows connection status for each
- [ ] Connect button initiates OAuth flow
- [ ] Disconnect button revokes and removes tokens
- [ ] Shows last sync time and any errors

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

(Not started)
