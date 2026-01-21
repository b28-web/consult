# Submission Queue Pattern

## Overview

All inbound communications flow through a `Submission` table before being processed into `Message` records. This decouples intake from processing.

## The Pattern

```
[Edge]                    [Database]                [Django]
Worker receives    →    Submission row      →    Process task
form/SMS/voice          (raw, unprocessed)       creates Contact + Message
```

### 1. Worker Writes Raw Submission

```typescript
await sql`
  INSERT INTO inbox_submission (id, client_slug, channel, payload, source_url, created_at)
  VALUES (${id}, ${clientSlug}, ${channel}, ${payload}::jsonb, ${sourceUrl}, NOW())
`;
```

### 2. Django Polls Unprocessed

```python
def process_pending_submissions():
    pending = Submission.objects.filter(processed_at__isnull=True)
    for submission in pending:
        try:
            process_submission(submission)
            submission.processed_at = timezone.now()
            submission.save()
        except Exception as e:
            submission.error = str(e)
            submission.save()
```

### 3. Processing Creates Contact + Message

```python
def process_submission(submission: Submission) -> Message:
    client = Client.objects.get(slug=submission.client_slug)
    payload = submission.payload

    # Find or create contact
    contact, _ = Contact.objects.get_or_create(
        client=client,
        email=payload.get("email"),
        defaults={"name": payload.get("name")}
    )

    # Create message
    message = Message.objects.create(
        client=client,
        contact=contact,
        channel=submission.channel,
        body=payload.get("message"),
        source_url=submission.source_url,
    )

    # Link submission to message
    submission.message = message
    return message
```

## Benefits

1. **Fast intake**: Workers return immediately, no processing delay
2. **Resilience**: If processing fails, submission is preserved
3. **Audit trail**: Raw intake data is never lost
4. **Retry**: Failed submissions can be reprocessed

## Schema

```sql
CREATE TABLE inbox_submission (
    id UUID PRIMARY KEY,
    client_slug VARCHAR(100) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    payload JSONB NOT NULL,
    source_url VARCHAR(200),
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    error TEXT,
    message_id INTEGER REFERENCES inbox_message(id)
);

CREATE INDEX ON inbox_submission (client_slug, processed_at)
    WHERE processed_at IS NULL;
```
