"""
URL routing for restaurant API endpoints.

Most endpoints are public (no auth required) and CORS-enabled.
"""

from django.urls import path

from apps.web.restaurant import views

app_name = "restaurant"

urlpatterns = [
    # Menu endpoints
    path("menu", views.menu_list, name="menu_list"),
    path("menu/<int:menu_id>", views.menu_detail, name="menu_detail"),
    # Availability endpoint (for 86'd polling)
    path("availability", views.availability, name="availability"),
    # Manual sync endpoint (authenticated)
    path("sync-availability", views.sync_availability, name="sync_availability"),
    # Order endpoints
    path("orders", views.create_order, name="order_create"),
    path("orders/<int:order_id>", views.get_order, name="order_detail"),
    path("orders/<int:order_id>/confirm", views.confirm_order, name="order_confirm"),
    path("orders/<int:order_id>/status", views.order_status, name="order_status"),
]
