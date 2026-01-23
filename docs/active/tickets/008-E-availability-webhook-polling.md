# 008-E: 86'd Item Webhook Handler and Availability Polling

**EP:** [EP-008-restaurant-pos-integration](../enhancement_proposals/EP-008-restaurant-pos-integration.md)
**Status:** complete
**Phase:** 2 (POS Read Integration)

## Summary

Implement the webhook handler for POS inventory/availability events and the polling mechanism for 86'd item updates. When a POS system sends an availability change webhook, update the `MenuItem.is_available` field in real-time.

## Acceptance Criteria

- [x] Intake worker route: `POST /intake/{slug}/pos/{provider}`
- [x] Webhook signature verification per provider
- [x] `pos_webhook_event` table for webhook audit trail
- [x] Django task to process availability webhooks
- [x] `MenuItem.is_available` updated on webhook receipt
- [x] `MenuItem.availability_updated_at` timestamp updated
- [x] Availability API endpoint returns fresh data (low cache TTL)
- [x] Fallback: Manual sync endpoint `POST /api/clients/{slug}/sync-availability`
- [x] Webhook replay/retry handling (idempotent)
- [x] Monitoring: Log webhook processing latency
- [x] Integration tests with mock webhooks

## Implementation Notes

### Webhook Flow

```
POS System
    │
    │ POST /intake/{slug}/pos/toast
    │ Headers: X-Toast-Signature: ...
    │ Body: { "eventType": "ITEM_AVAILABILITY_CHANGED", ... }
    │
    ▼
Intake Worker (Cloudflare)
    │
    │ 1. Validate signature (optional at edge, required in Django)
    │ 2. Write to pos_webhook_event table
    │ 3. Return 202 Accepted
    │
    ▼
Django Async Task
    │
    │ 1. Load webhook from pos_webhook_event
    │ 2. Verify signature with provider-specific logic
    │ 3. Parse event type
    │ 4. Route to handler
    │
    ▼
Availability Handler
    │
    │ 1. Extract item external_id and availability
    │ 2. MenuItem.objects.filter(external_id=...).update(is_available=...)
    │ 3. Mark webhook as processed
```

### Database Schema

```python
# apps/web/pos/models.py

class POSWebhookEvent(models.Model):
    """Audit trail for POS webhooks."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    client = models.ForeignKey("core.Client", on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)  # toast, clover, square
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    signature = models.CharField(max_length=500)

    # Processing status
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)
    error = models.TextField(blank=True)

    # Idempotency
    external_event_id = models.CharField(max_length=255, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "processed_at"]),
            models.Index(fields=["external_event_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "external_event_id"],
                name="unique_webhook_event",
                condition=models.Q(external_event_id__isnull=False),
            )
        ]
```

### Intake Worker Route

```typescript
// workers/intake/src/routes/pos.ts

export async function handlePOSWebhook(
  request: Request,
  env: Env,
  clientSlug: string,
  provider: string
): Promise<Response> {
  const signature = request.headers.get(`X-${provider}-Signature`) || "";
  const payload = await request.json();

  // Extract event ID for idempotency (provider-specific)
  const externalEventId = extractEventId(provider, payload);

  await sql`
    INSERT INTO pos_webhook_event
      (id, client_slug, provider, event_type, payload, signature, external_event_id, received_at)
    VALUES
      (${crypto.randomUUID()}, ${clientSlug}, ${provider},
       ${payload.eventType || payload.type || "unknown"},
       ${JSON.stringify(payload)}, ${signature}, ${externalEventId}, NOW())
    ON CONFLICT (client_slug, external_event_id)
      WHERE external_event_id IS NOT NULL
    DO NOTHING
  `;

  return new Response(JSON.stringify({ status: "accepted" }), {
    status: 202,
    headers: { "Content-Type": "application/json" },
  });
}
```

### Django Task

```python
# apps/web/pos/tasks.py

from consult.tasks import shared_task

@shared_task
def process_pos_webhook(webhook_id: str) -> None:
    webhook = POSWebhookEvent.objects.get(id=webhook_id)

    if webhook.processed_at:
        return  # Already processed (idempotent)

    try:
        adapter = get_adapter(webhook.provider)

        # Verify signature
        if not adapter.verify_webhook_signature(
            json.dumps(webhook.payload).encode(),
            webhook.signature,
            get_webhook_secret(webhook.client, webhook.provider),
        ):
            raise ValueError("Invalid webhook signature")

        # Parse and route
        event = adapter.parse_webhook(webhook.payload)
        handle_pos_event(webhook.client, event)

        webhook.processed_at = timezone.now()
        webhook.save(update_fields=["processed_at"])

    except Exception as e:
        webhook.error = str(e)
        webhook.save(update_fields=["error"])
        raise


def handle_pos_event(client: Client, event: POSWebhookEvent) -> None:
    match event.event_type:
        case "item_availability_changed":
            handle_availability_change(client, event)
        case "menu_updated":
            trigger_full_menu_sync(client)
        case "order_status_changed":
            handle_order_status_change(client, event)


def handle_availability_change(client: Client, event: POSWebhookEvent) -> None:
    for item in event.items:
        MenuItem.objects.filter(
            client=client,
            external_id=item.external_id,
        ).update(
            is_available=item.is_available,
            availability_updated_at=timezone.now(),
        )
```

### Provider-Specific Event Types

**Toast:**
- `ITEM_AVAILABILITY_CHANGED` - Item 86'd or restored
- `MENU_UPDATED` - Full menu sync needed

**Clover:**
- `inventory.updated` - Stock level change
- `items.updated` - Item modified

**Square:**
- `inventory.count.updated` - Inventory change
- `catalog.version.updated` - Catalog change

### Sync Fallback Endpoint

```python
# apps/web/restaurant/views.py

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_availability(request, slug: str) -> Response:
    """Manual trigger to sync availability from POS."""
    client = get_object_or_404(Client, slug=slug)

    # Requires staff permission
    if request.user.client != client:
        raise PermissionDenied()

    profile = RestaurantProfile.objects.get(client=client)
    if not profile.pos_provider:
        return Response({"error": "No POS configured"}, status=400)

    # Trigger async sync
    sync_menu_availability.delay(client.id)

    return Response({"status": "sync_started"})
```

## Dependencies

- 008-A (POS adapter interface for signature verification and event parsing)
- 008-B (MenuItem model must exist)
- 008-C (Availability API endpoint)

## Progress

### 2026-01-23: Implementation Complete

**Files created/modified:**
- `apps/web/pos/models.py` - POSWebhookEvent model with idempotency constraint
- `apps/web/pos/admin.py` - Admin registration for POSWebhookEvent
- `apps/web/pos/migrations/0001_add_poswebhookevent.py` - Database migration
- `apps/web/pos/services/__init__.py` - Service exports
- `apps/web/pos/services/webhook_processor.py` - Webhook processing service
- `workers/intake/src/index.ts` - POS webhook route handler
- `apps/web/restaurant/views.py` - Manual sync endpoint
- `apps/web/restaurant/urls.py` - URL routing for sync endpoint
- `apps/web/pos/tests/test_webhook_processor.py` - Integration tests

**Key design decisions:**
1. Webhook writes are idempotent via `external_event_id` unique constraint
2. Transaction commits failed status before re-raising exception
3. Late imports used to avoid circular dependencies
4. Currently uses MockPOSAdapter for all providers (real adapters in 008-F+)
