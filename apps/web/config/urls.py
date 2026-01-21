"""
URL configuration for Consult.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/inbox/", include("apps.web.inbox.urls")),
    path("dashboard/crm/", include("apps.web.crm.urls")),
]
