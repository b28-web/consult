"""
CRM URL routes.
"""

from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    # Contacts
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/<int:contact_id>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:contact_id>/info/", views.contact_info, name="contact_info"),
    path("contacts/<int:contact_id>/edit/", views.contact_edit, name="contact_edit"),
    path("contacts/<int:contact_id>/notes/", views.add_note, name="add_note"),
    # Jobs
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<int:job_id>/", views.job_detail, name="job_detail"),
]
