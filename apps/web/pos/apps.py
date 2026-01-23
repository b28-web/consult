"""Django app configuration for POS integration."""

from django.apps import AppConfig


class PosConfig(AppConfig):
    """POS integration app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web.pos"
    verbose_name = "POS Integration"
