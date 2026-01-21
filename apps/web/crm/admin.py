"""Admin registrations for CRM models."""

from django.contrib import admin

from .models import Job, Note, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "color", "client"]
    list_filter = ["client"]
    search_fields = ["name"]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["title", "contact", "status", "scheduled_at", "client"]
    list_filter = ["client", "status"]
    search_fields = ["title", "contact__name"]
    raw_id_fields = ["contact"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["content_preview", "contact", "job", "author", "created_at"]
    list_filter = ["client"]
    search_fields = ["content"]
    raw_id_fields = ["contact", "job", "author"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Content")
    def content_preview(self, obj: Note) -> str:
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
