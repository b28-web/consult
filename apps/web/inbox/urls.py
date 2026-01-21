"""
Inbox URL routes.
"""

from django.urls import path

from . import views

app_name = "inbox"

urlpatterns = [
    path("", views.inbox_list, name="list"),
    path("<int:message_id>/", views.message_detail, name="detail"),
    path("<int:message_id>/reply/", views.message_reply, name="reply"),
    path("<int:message_id>/mark/", views.message_mark, name="mark"),
]
