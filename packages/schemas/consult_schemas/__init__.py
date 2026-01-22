"""Consult Schemas - Pydantic models for data contracts."""

from consult_schemas.classification import (
    MessageCategory,
    MessageClassification,
    MessageIntent,
    SuggestedAction,
)
from consult_schemas.forms import ContactFormSubmission, QuoteRequestSubmission
from consult_schemas.webhooks import (
    CalComBooking,
    CalComWebhookPayload,
    JobberWebhookPayload,
    TwilioSMSPayload,
    TwilioVoicePayload,
)

__all__ = [
    "CalComBooking",
    "CalComWebhookPayload",
    "ContactFormSubmission",
    "JobberWebhookPayload",
    "MessageCategory",
    "MessageClassification",
    "MessageIntent",
    "QuoteRequestSubmission",
    "SuggestedAction",
    "TwilioSMSPayload",
    "TwilioVoicePayload",
]
