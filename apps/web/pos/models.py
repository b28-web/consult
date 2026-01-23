"""POS webhook models - audit trail for POS webhook events."""

import uuid

from django.db import models

from apps.web.restaurant.models import POSProvider


class WebhookStatus(models.TextChoices):
    """Webhook processing status."""

    PENDING = "pending", "Pending"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"  # e.g., duplicate event


class POSWebhookEvent(models.Model):
    """
    Audit trail for POS webhook events.

    Stores raw webhook payloads for debugging and reprocessing.
    Supports idempotency via external_event_id.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Client association
    client = models.ForeignKey(
        "core.Client",
        on_delete=models.CASCADE,
        related_name="pos_webhook_events",
    )

    # Provider info
    provider = models.CharField(
        max_length=20,
        choices=POSProvider.choices,
    )
    event_type = models.CharField(
        max_length=100,
        help_text="Event type from the POS system",
    )

    # Payload
    payload = models.JSONField(
        help_text="Raw webhook payload",
    )
    signature = models.CharField(
        max_length=500,
        blank=True,
        help_text="Signature header for verification",
    )

    # Idempotency
    external_event_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Event ID from the POS system (for deduplication)",
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.PENDING,
    )
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(
        blank=True,
        help_text="Error message if processing failed",
    )

    # Processing metrics
    processing_duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time to process webhook in milliseconds",
    )

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["client", "received_at"]),
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["external_event_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "provider", "external_event_id"],
                name="unique_pos_webhook_event",
                condition=models.Q(external_event_id__gt=""),
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type} ({self.status})"
