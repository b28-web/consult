# Multi-Tenancy Pattern

## Overview

All data in Consult is scoped to a `Client` (tenant). This document describes how tenant isolation is enforced.

## The Pattern

### 1. ClientScopedModel

All tenant-scoped models inherit from this abstract base:

```python
class ClientScopedModel(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ClientScopedManager()

    class Meta:
        abstract = True
```

### 2. ClientScopedManager

Custom manager that requires explicit client filtering:

```python
# CORRECT - always use for_client()
messages = Message.objects.for_client(request).all()

# WRONG - bypasses tenant isolation
messages = Message.objects.all()  # Never do this!
```

### 3. ClientMiddleware

Attaches `request.client` based on:
1. `X-Client-ID` header (API calls)
2. Subdomain (`{client}.consult.io`)
3. User's assigned client (dashboard)

### 4. View Pattern

Every view that accesses tenant data must use `for_client()`:

```python
def inbox_list(request: HttpRequest) -> HttpResponse:
    messages = Message.objects.for_client(request).all()
    # ...
```

## Security Considerations

- **Never** use raw querysets on ClientScopedModel subclasses
- **Always** use `for_client(request)` in views
- Tests must verify cross-tenant data is inaccessible
- Admin should only show data for superuser's context

## Testing

```python
def test_tenant_isolation(client_a, client_b):
    # Create message for client A
    msg = Message.objects.create(client=client_a, ...)

    # Request as client B should not see it
    request = mock_request(client=client_b)
    messages = Message.objects.for_client(request)
    assert msg not in messages
```
