# 002-A: Submission Processing Task

**EP:** [EP-002-inbox-processing](../enhancement_proposals/EP-002-inbox-processing.md)
**Status:** pending

## Summary

Create a Django management command that polls unprocessed submissions and converts them into Contact + Message records.

## Acceptance Criteria

- [ ] `process_submissions` management command created
- [ ] Polls `Submission.objects.filter(processed_at__isnull=True)`
- [ ] Finds or creates Contact by email (primary) or phone (fallback)
- [ ] Creates Message with correct channel, body, source_url
- [ ] Marks submission as processed with timestamp
- [ ] Handles errors gracefully (logs, marks error, continues)
- [ ] Can run via `doppler run -- uv run python manage.py process_submissions`

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

(Not started)
