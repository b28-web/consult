# HTMX + Django Pattern

## Overview

The dashboard uses HTMX for interactivity. Django views return HTML fragments, not JSON.

## The Pattern

### 1. View Returns HTML Fragment

```python
def inbox_list(request: HttpRequest) -> HttpResponse:
    messages = Message.objects.for_client(request).all()
    return render(request, "inbox/partials/message_list.html", {
        "messages": messages
    })
```

### 2. Template is a Partial

```html
<!-- inbox/partials/message_list.html -->
{% for message in messages %}
<div class="message-row" id="message-{{ message.id }}">
  <span>{{ message.contact.name }}</span>
  <span>{{ message.body|truncatewords:20 }}</span>
  <button
    hx-post="{% url 'inbox:mark' message.id %}"
    hx-vals='{"status": "read"}'
    hx-swap="outerHTML"
    hx-target="#message-{{ message.id }}"
  >
    Mark Read
  </button>
</div>
{% endfor %}
```

### 3. HTMX Attributes

| Attribute | Purpose |
|-----------|---------|
| `hx-get` / `hx-post` | HTTP method + URL |
| `hx-target` | Element to update (CSS selector) |
| `hx-swap` | How to insert (`innerHTML`, `outerHTML`, `beforeend`, etc.) |
| `hx-vals` | Extra data to send |
| `hx-indicator` | Loading spinner element |
| `hx-trigger` | Event that triggers request |

### 4. Response Patterns

**Replace element:**
```python
# hx-swap="outerHTML" hx-target="#message-123"
return render(request, "inbox/partials/message_row.html", {"message": message})
```

**Append to list:**
```python
# hx-swap="beforeend" hx-target="#message-list"
return render(request, "inbox/partials/message_row.html", {"message": new_message})
```

**Show error:**
```python
# hx-target-error="#form-errors"
return render(request, "partials/error.html", {"error": "Invalid input"}, status=400)
```

## URL Conventions

```
/dashboard/inbox/                    # List (GET)
/dashboard/inbox/{id}/               # Detail (GET)
/dashboard/inbox/{id}/reply/         # Action (POST)
/dashboard/inbox/{id}/mark/          # Action (POST)
```

## Testing

Test that views return proper HTML fragments:

```python
def test_inbox_list_returns_html(client, user):
    client.force_login(user)
    response = client.get("/dashboard/inbox/")
    assert response.status_code == 200
    assert "message-row" in response.content.decode()
```
