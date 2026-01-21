# 004-C: Jobber OAuth Integration

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** pending

## Summary

Implement OAuth flow to connect client's Jobber account.

## Acceptance Criteria

- [ ] OAuth authorization URL generation
- [ ] Callback handler exchanges code for tokens
- [ ] Tokens stored encrypted in Integration model
- [ ] Token refresh on expiry
- [ ] Disconnect/revoke functionality
- [ ] Dashboard UI to initiate connection

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

(Not started)
