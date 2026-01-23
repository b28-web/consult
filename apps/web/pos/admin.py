"""Admin registration for POS models."""

from django.contrib import admin

from apps.web.pos.models import POSWebhookEvent


@admin.register(POSWebhookEvent)
class POSWebhookEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin for POS webhook events."""

    list_display = [
        "id",
        "client",
        "provider",
        "event_type",
        "status",
        "received_at",
        "processed_at",
    ]
    list_filter = ["provider", "event_type", "status"]
    search_fields = ["client__name", "external_event_id"]
    readonly_fields = [
        "id",
        "received_at",
        "processed_at",
        "processing_duration_ms",
    ]
    ordering = ["-received_at"]
    date_hierarchy = "received_at"
