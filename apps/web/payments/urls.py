"""
URL routing for payment endpoints.
"""

from django.urls import path

from apps.web.payments import webhooks

app_name = "payments"

urlpatterns = [
    path("webhooks/stripe", webhooks.stripe_webhook, name="stripe-webhook"),
]
