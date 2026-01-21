"""Admin registrations for inbox models."""

from django.contrib import admin

from .models import Contact, Message, Submission


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "email", "phone", "client", "message_count"]
    list_filter = ["client"]
    search_fields = ["name", "email", "phone"]
    readonly_fields = ["created_at", "updated_at", "message_count", "last_message_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["contact", "channel", "direction", "status", "received_at"]
    list_filter = ["client", "channel", "direction", "status"]
    search_fields = ["contact__name", "contact__email", "subject", "body"]
    readonly_fields = ["created_at", "updated_at", "received_at"]
    raw_id_fields = ["contact"]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "client_slug", "channel", "created_at", "processed_at"]
    list_filter = ["channel", "client_slug"]
    search_fields = ["client_slug"]
    readonly_fields = ["id", "created_at", "processed_at", "payload"]
    raw_id_fields = ["message"]
