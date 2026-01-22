from django.contrib import admin

from apps.web.integrations.models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = [
        "client",
        "provider",
        "is_active",
        "external_account_name",
        "connected_at",
    ]
    list_filter = ["provider", "is_active"]
    search_fields = ["client__name", "external_account_name"]
    readonly_fields = ["connected_at", "last_used_at"]
