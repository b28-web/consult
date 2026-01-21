# 003-F: Reply Channel Selection Logic

**EP:** [EP-003-communications](../enhancement_proposals/EP-003-communications.md)
**Status:** pending

## Summary

Smart defaults for reply channel based on original message and contact info.

## Acceptance Criteria

- [ ] Reply form pre-selects channel matching original message
- [ ] If original was SMS → default to SMS (if phone available)
- [ ] If original was form/email → default to email
- [ ] If original was voicemail → default to SMS callback
- [ ] Allow override if contact has both email and phone
- [ ] Disable unavailable channels (no phone = no SMS option)

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

(Not started)
