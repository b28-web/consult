"""Consult Schemas - Pydantic models for data contracts."""

from consult_schemas.classification import (
    MessageCategory,
    MessageClassification,
    MessageIntent,
    SuggestedAction,
)
from consult_schemas.forms import ContactFormSubmission, QuoteRequestSubmission
from consult_schemas.pos import (
    ItemAvailabilityChangedEvent,
    MenuUpdatedEvent,
    OrderStatus,
    OrderStatusChangedEvent,
    OrderType,
    PaymentStatus,
    POSCredentials,
    POSMenu,
    POSMenuCategory,
    POSMenuItem,
    POSModifier,
    POSModifierGroup,
    POSOrder,
    POSOrderItem,
    POSOrderItemModifier,
    POSOrderResult,
    POSOrderStatus,
    POSProvider,
    POSSession,
    POSWebhookEvent,
)
from consult_schemas.webhooks import (
    CalComBooking,
    CalComWebhookPayload,
    JobberWebhookPayload,
    TwilioSMSPayload,
    TwilioVoicePayload,
)

__all__ = [
    # Classification
    "MessageCategory",
    "MessageClassification",
    "MessageIntent",
    "SuggestedAction",
    # Forms
    "ContactFormSubmission",
    "QuoteRequestSubmission",
    # Webhooks
    "CalComBooking",
    "CalComWebhookPayload",
    "JobberWebhookPayload",
    "TwilioSMSPayload",
    "TwilioVoicePayload",
    # POS
    "ItemAvailabilityChangedEvent",
    "MenuUpdatedEvent",
    "OrderStatus",
    "OrderStatusChangedEvent",
    "OrderType",
    "PaymentStatus",
    "POSCredentials",
    "POSMenu",
    "POSMenuCategory",
    "POSMenuItem",
    "POSModifier",
    "POSModifierGroup",
    "POSOrder",
    "POSOrderItem",
    "POSOrderItemModifier",
    "POSOrderResult",
    "POSOrderStatus",
    "POSProvider",
    "POSSession",
    "POSWebhookEvent",
]
