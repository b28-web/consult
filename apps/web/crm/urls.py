"""
CRM URL routes.
"""

from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/<int:contact_id>/", views.contact_detail, name="contact_detail"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<int:job_id>/", views.job_detail, name="job_detail"),
]
