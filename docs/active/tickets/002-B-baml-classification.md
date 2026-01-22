# 002-B: BAML Classification Integration

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Integrate BAML classification into the submission processing flow. After creating a Message, call `ClassifyMessage()` and store the results.

## Acceptance Criteria

- [x] `baml_client/` generated and importable in Django
- [x] Classification called during submission processing
- [x] Message fields populated: category, intent, urgency, suggested_action, ai_confidence
- [x] Extracted contact info (name, phone, email, address) used to enrich Contact
- [x] Handles BAML/API errors gracefully (message still created, just unclassified)
- [x] Classification logged for debugging

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

### 2026-01-22

Implemented BAML classification integration with:

**Dependencies added:**
- `baml-py==0.217.0` added to pyproject.toml

**Model changes:**
- Added `Client.Vertical` enum with business types (junk_hauler, barber, cleaning, etc.)
- Added `Client.vertical` field with choices
- Added `Message.ai_summary` field for AI-generated summary
- Added `Message.is_new_lead` boolean field
- Added `Contact.address` field for extracted service addresses
- Created migrations: `0002_add_client_vertical.py`, `0002_add_classification_fields.py`

**process_submissions.py updates:**
- Added `--skip-classification` flag for testing without AI
- Added `_classify_message()` method that calls BAML ClassifyMessage
- Added `_enrich_contact_from_classification()` method to update contact with extracted info
- Classification errors are logged but don't fail submission processing
- Classification runs after submission is marked as processed (non-blocking)

**Classification flow:**
1. Submission processed into Message (as before)
2. If not `--skip-classification`, call `b.ClassifyMessage()`
3. Store results: category, intent, urgency, suggested_action, confidence, summary, is_new_lead
4. Enrich contact with any extracted name/email/phone/address (only if field is empty)
5. Log classification results for debugging

**Tests added (6 new, 16 total):**
- test_classification_populates_message_fields
- test_classification_enriches_contact
- test_classification_does_not_overwrite_existing_contact_data
- test_classification_failure_does_not_fail_submission
- test_skip_classification_flag_skips_ai
- test_client_vertical_passed_to_classifier

**Quality:**
- All ruff checks pass
- All mypy checks pass
- All 16 tests pass

**Usage:**
```bash
# With classification (default)
doppler run -- uv run python apps/web/manage.py process_submissions --once

# Without classification (for testing)
doppler run -- uv run python apps/web/manage.py process_submissions --once \
    --skip-classification
```

**Environment requirement:**
- `GOOGLE_API_KEY` must be set in Doppler for Gemini 2.5 Flash API access
