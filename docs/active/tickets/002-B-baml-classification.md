# 002-B: BAML Classification Integration

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Integrate BAML classification into the submission processing flow. After creating a Message, call `ClassifyMessage()` and store the results.

## Acceptance Criteria

- [ ] `baml_client/` generated and importable in Django
- [ ] Classification called during submission processing
- [ ] Message fields populated: category, intent, urgency, suggested_action, ai_confidence
- [ ] Extracted contact info (name, phone, email, address) used to enrich Contact
- [ ] Handles BAML/API errors gracefully (message still created, just unclassified)
- [ ] Classification logged for debugging

## Implementation Notes

```
# Generate BAML client
baml-cli generate

# In process_submissions.py
from baml_client import b

result = b.ClassifyMessage(
    message_content=submission.payload.get("message", ""),
    message_source=submission.channel,
    client_vertical=client.vertical,  # Add vertical field to Client model
)

message.category = result.category.value
message.intent = result.intent.value
message.urgency = str(result.urgency)
message.suggested_action = result.suggested_action.value
message.ai_confidence = result.confidence
message.save()
```

May need to add `vertical` field to Client model:
```python
class Client(models.Model):
    # ...
    vertical = models.CharField(max_length=50, default="general")
    # Options: junk_hauler, barber, cleaning, landscaper, coffee_shop, etc.
```

## Progress

(Not started)
