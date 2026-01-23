"""
URL configuration for Consult.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", include("apps.web.dashboard.urls")),
    path("dashboard/inbox/", include("apps.web.inbox.urls")),
    path("dashboard/crm/", include("apps.web.crm.urls")),
    path("dashboard/integrations/", include("apps.web.integrations.urls")),
    # Public API endpoints
    path("api/clients/<slug:slug>/", include("apps.web.restaurant.urls")),
]
