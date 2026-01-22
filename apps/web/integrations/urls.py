from django.urls import path

from apps.web.integrations import views

app_name = "integrations"

urlpatterns = [
    # Jobber OAuth
    path("jobber/authorize/", views.jobber_authorize, name="jobber_authorize"),
    path("jobber/callback/", views.jobber_callback, name="jobber_callback"),
    path("jobber/disconnect/", views.jobber_disconnect, name="jobber_disconnect"),
]
