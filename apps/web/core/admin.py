"""Admin registrations for core models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Client, User


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "slug", "email", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "email"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    list_display = ["username", "email", "client", "role", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "role", "client"]
    search_fields = ["username", "email"]
    fieldsets = (
        *BaseUserAdmin.fieldsets,  # type: ignore[misc]
        ("Client Info", {"fields": ("client", "role")}),
    )
    add_fieldsets = (
        *BaseUserAdmin.add_fieldsets,
        ("Client Info", {"fields": ("client", "role")}),
    )
