# 002-A: Submission Processing Task

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** complete

## Summary

Create a Django management command that polls unprocessed submissions and converts them into Contact + Message records.

## Acceptance Criteria

- [x] `process_submissions` management command created
- [x] Polls `Submission.objects.filter(processed_at__isnull=True)`
- [x] Finds or creates Contact by email (primary) or phone (fallback)
- [x] Creates Message with correct channel, body, source_url
- [x] Marks submission as processed with timestamp
- [x] Handles errors gracefully (logs, marks error, continues)
- [x] Can run via `doppler run -- uv run python manage.py process_submissions`

## Implementation Notes

```
apps/web/inbox/management/commands/process_submissions.py
```

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        pending = Submission.objects.filter(processed_at__isnull=True)
        for submission in pending:
            try:
                message = self.process_one(submission)
                submission.message = message
                submission.processed_at = timezone.now()
                submission.save()
            except Exception as e:
                submission.error = str(e)
                submission.save()
                self.stderr.write(f"Error: {e}")
```

Contact matching logic:
1. If email provided: `get_or_create(client=client, email=email)`
2. Elif phone provided: `get_or_create(client=client, phone=phone)`
3. Update contact name if provided and better than existing

## Progress

### 2026-01-22

Implemented the `process_submissions` management command with:

**Files created:**
- `apps/web/inbox/management/__init__.py`
- `apps/web/inbox/management/commands/__init__.py`
- `apps/web/inbox/management/commands/process_submissions.py`
- `apps/web/conftest.py` - pytest fixtures
- `apps/web/inbox/tests/__init__.py`
- `apps/web/inbox/tests/factories.py` - factory_boy factories
- `apps/web/inbox/tests/test_process_submissions.py` - 10 tests

**Features:**
- Polls pending submissions with `--once` flag for single pass or continuous polling (default 30s)
- Looks up Client by slug, finds/creates Contact by email then phone
- Creates Message with proper channel mapping
- Atomic transactions per submission
- Graceful error handling with error logged to submission.error field
- Phone number normalization
- Email normalization to lowercase
- Updates contact name if current name is empty

**Tests (10 passing):**
- test_processes_pending_submission
- test_matches_existing_contact_by_email
- test_matches_existing_contact_by_phone
- test_handles_unknown_client_slug
- test_handles_missing_email_and_phone
- test_handles_unknown_channel
- test_skips_already_processed_submissions
- test_normalizes_email_to_lowercase
- test_processes_multiple_submissions
- test_updates_contact_name_if_empty

**Quality:**
- All ruff checks pass
- All mypy checks pass
- Added mypy override for test files (factory_boy lacks type stubs)
