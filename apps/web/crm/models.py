"""
CRM models - Jobs, Tags, Notes.

Lightweight CRM features for tracking customer work.
"""

from django.db import models

from apps.web.core.models import ClientScopedModel
from apps.web.inbox.models import Contact


class Tag(ClientScopedModel):
    """
    Tag for categorizing contacts and jobs.
    """

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#6366f1")  # Hex color

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "name"], name="unique_tag_per_client"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Job(ClientScopedModel):
    """
    A scheduled job/appointment.

    Can be linked to a Contact.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    # Location
    address = models.TextField(blank=True)

    # Pricing
    estimated_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # External integrations
    calcom_event_id = models.CharField(max_length=100, blank=True)
    jobber_id = models.CharField(max_length=100, blank=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="jobs")

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self) -> str:
        return self.title


class Note(ClientScopedModel):
    """
    Internal note on a contact or job.
    """

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notes",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notes",
    )

    content = models.TextField()
    author = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Note must be attached to contact or job (or both)
            models.CheckConstraint(
                condition=models.Q(contact__isnull=False) | models.Q(job__isnull=False),
                name="note_has_parent",
            ),
        ]

    def __str__(self) -> str:
        return f"Note by {self.author} on {self.created_at.date()}"
