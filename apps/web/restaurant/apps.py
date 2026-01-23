"""Django app configuration for restaurant module."""

from django.apps import AppConfig


class RestaurantConfig(AppConfig):
    """Restaurant app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web.restaurant"
    verbose_name = "Restaurant"
