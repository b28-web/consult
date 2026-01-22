# 003-F: Reply Channel Selection Logic

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** completed

## Summary

Smart defaults for reply channel based on original message and contact info.

## Acceptance Criteria

- [x] Reply form pre-selects channel matching original message
- [x] If original was SMS → default to SMS (if phone available)
- [x] If original was form/email → default to email
- [x] If original was voicemail → default to SMS callback
- [x] Allow override if contact has both email and phone
- [x] Disable unavailable channels (no phone = no SMS option)

## Implementation Notes

Logic in template/view:

```python
def get_reply_channels(message: Message, contact: Contact) -> list[dict]:
    """Return available reply channels with defaults."""
    channels = []

    if contact.email:
        channels.append({
            "value": "email",
            "label": f"Email ({contact.email})",
            "default": message.channel in ("form", "email"),
        })

    if contact.phone:
        channels.append({
            "value": "sms",
            "label": f"SMS ({contact.phone})",
            "default": message.channel in ("sms", "voicemail"),
        })

    return channels
```

In template:
```html
<select name="channel">
  {% for ch in reply_channels %}
  <option value="{{ ch.value }}" {% if ch.default %}selected{% endif %}>
    {{ ch.label }}
  </option>
  {% endfor %}
</select>
```

## Progress

### 2026-01-22
- Created `get_reply_channels()` helper function in views.py
- Smart defaults: SMS/voicemail → SMS, form/email → email
- Falls back to available channel if default not available
- Updated message_detail view to pass reply_channels to template
- Updated template to use dynamic channel options
- Shows message when no contact method available
- 7 new tests, all 63 inbox tests pass
