"""
Inbox models - Contacts, Messages, and Submissions.

Data flow:
1. Submissions come in from Workers (raw intake)
2. Processing creates/matches Contact
3. Message is created from Submission
4. AI classifies the Message
"""

import uuid

from django.db import models

from apps.web.core.models import ClientScopedModel


class Contact(ClientScopedModel):
    """
    A customer contact - someone who has reached out.

    Contacts are matched by email or phone.
    """

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True, help_text="Service/mailing address")

    # Denormalized stats (updated by signals/tasks)
    message_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)

    # CRM fields
    internal_notes = models.TextField(blank=True, help_text="Quick notes about contact")
    tags = models.ManyToManyField("crm.Tag", blank=True, related_name="contacts")

    class Meta:
        ordering = ["-last_message_at"]
        constraints = [
            # At least one contact method required
            models.CheckConstraint(
                condition=~models.Q(email="", phone=""),
                name="contact_has_email_or_phone",
            ),
        ]

    def __str__(self) -> str:
        return self.name or self.email or self.phone


class Message(ClientScopedModel):
    """
    An inbound or outbound message.

    Linked to a Contact, classified by AI.
    """

    class Channel(models.TextChoices):
        FORM = "form", "Web Form"
        SMS = "sms", "SMS"
        VOICEMAIL = "voicemail", "Voicemail"
        EMAIL = "email", "Email"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    class Status(models.TextChoices):
        UNREAD = "unread", "Unread"
        READ = "read", "Read"
        REPLIED = "replied", "Replied"
        ARCHIVED = "archived", "Archived"

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    channel = models.CharField(max_length=20, choices=Channel.choices)
    direction = models.CharField(
        max_length=20,
        choices=Direction.choices,
        default=Direction.INBOUND,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNREAD,
    )

    # Content
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    source_url = models.URLField(blank=True, help_text="Page form was submitted from")

    # External provider ID (e.g., Twilio message SID)
    external_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="External provider message ID (Twilio SID, etc.)",
    )

    # AI classification (nullable until processed)
    category = models.CharField(max_length=50, blank=True)
    intent = models.CharField(max_length=50, blank=True)
    urgency = models.CharField(max_length=20, blank=True)
    suggested_action = models.CharField(max_length=100, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_summary = models.TextField(blank=True, help_text="AI-generated message summary")
    is_new_lead = models.BooleanField(
        default=False, help_text="AI determined this is a new lead"
    )

    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.get_channel_display()} from {self.contact}"


class Submission(models.Model):
    """
    Raw intake submission - written by Workers, processed by Django.

    This is the "queue" between edge intake and backend processing.
    Submissions are immutable once created.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Client lookup (slug, not FK - workers don't have DB access)
    client_slug = models.CharField(max_length=100, db_index=True)

    channel = models.CharField(max_length=20)  # form, sms, voicemail, email
    payload = models.JSONField(help_text="Raw submission data")
    source_url = models.URLField(blank=True)

    # Processing state
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error = models.TextField(blank=True, help_text="Processing error if any")

    # Result (set after processing)
    message = models.OneToOneField(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submission",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["client_slug", "processed_at"],
                name="submission_unprocessed_idx",
            ),
        ]

    def __str__(self) -> str:
        status = "processed" if self.processed_at else "pending"
        return f"{self.channel} submission ({status})"
