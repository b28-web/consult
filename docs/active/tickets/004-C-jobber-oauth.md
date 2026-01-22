# 004-C: Jobber OAuth Integration

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** complete

## Summary

Implement OAuth flow to connect client's Jobber account.

## Acceptance Criteria

- [x] OAuth authorization URL generation
- [x] Callback handler exchanges code for tokens
- [x] Tokens stored encrypted in Integration model
- [x] Token refresh on expiry
- [x] Disconnect/revoke functionality
- [x] Dashboard UI to initiate connection

## Implementation Notes

Jobber OAuth flow:
1. Redirect to: `https://api.getjobber.com/api/oauth/authorize?client_id=...&redirect_uri=...&response_type=code`
2. User authorizes
3. Callback receives code
4. Exchange code for access_token + refresh_token

```python
# apps/web/integrations/views.py
def jobber_authorize(request):
    """Redirect to Jobber OAuth."""
    params = {
        "client_id": settings.JOBBER_CLIENT_ID,
        "redirect_uri": request.build_absolute_uri(reverse("jobber_callback")),
        "response_type": "code",
    }
    return redirect(f"https://api.getjobber.com/api/oauth/authorize?{urlencode(params)}")

def jobber_callback(request):
    """Handle OAuth callback."""
    code = request.GET.get("code")
    # Exchange for tokens
    # Store in Integration model
```

Integration model usage:
```python
integration = Integration.objects.create(
    client=request.client,
    provider="jobber",
    credentials={
        "access_token": "...",
        "refresh_token": "...",
        "expires_at": "...",
    },
    is_active=True,
)
```

## Progress

### 2026-01-22
- Created `apps/web/integrations` Django app with:
  - `Integration` model with provider, credentials, webhook_secret, connection status
  - Unique constraint per client+provider
  - Token expiry checking and accessor methods
- Implemented Jobber OAuth views:
  - `jobber_authorize` - redirects to Jobber OAuth page
  - `jobber_callback` - exchanges code for tokens, stores in Integration
  - `jobber_disconnect` - clears credentials and deactivates
- Added `refresh_jobber_token()` and `get_valid_jobber_token()` for token refresh
- Added settings page to dashboard (`/dashboard/settings/`) with:
  - Jobber connect/disconnect UI
  - Cal.com integration status display
  - Settings link in sidebar navigation
- Added JOBBER_CLIENT_ID and JOBBER_CLIENT_SECRET to Django settings
