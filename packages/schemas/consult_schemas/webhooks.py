"""Webhook payload schemas for external integrations."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# =============================================================================
# Cal.com Webhooks
# =============================================================================


class CalComAttendee(BaseModel):
    """Attendee in a Cal.com booking."""

    name: str
    email: EmailStr
    timezone: str
    language: str | None = None


class CalComBooking(BaseModel):
    """Cal.com booking details."""

    id: int
    uid: str
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    timezone: str
    location: str | None = None
    status: str  # "ACCEPTED", "PENDING", "CANCELLED", etc.
    attendees: list[CalComAttendee]
    metadata: dict | None = None


class CalComWebhookPayload(BaseModel):
    """Cal.com webhook payload structure."""

    trigger_event: str = Field(
        description="Event type: BOOKING_CREATED, BOOKING_CANCELLED, etc."
    )
    created_at: datetime
    payload: CalComBooking


# =============================================================================
# Twilio Webhooks
# =============================================================================


class TwilioSMSPayload(BaseModel):
    """Twilio incoming SMS webhook payload."""

    message_sid: str = Field(alias="MessageSid")
    account_sid: str = Field(alias="AccountSid")
    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")
    body: str = Field(alias="Body")
    num_media: int = Field(default=0, alias="NumMedia")
    media_urls: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class TwilioVoicePayload(BaseModel):
    """Twilio incoming voice/voicemail webhook payload."""

    call_sid: str = Field(alias="CallSid")
    account_sid: str = Field(alias="AccountSid")
    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")
    call_status: str = Field(alias="CallStatus")
    direction: str = Field(alias="Direction")
    recording_url: str | None = Field(default=None, alias="RecordingUrl")
    recording_duration: int | None = Field(default=None, alias="RecordingDuration")
    transcription_text: str | None = Field(default=None, alias="TranscriptionText")

    class Config:
        populate_by_name = True


# =============================================================================
# Jobber Webhooks
# =============================================================================


class JobberWebhookPayload(BaseModel):
    """Jobber webhook payload structure."""

    event: str = Field(description="Event type: client.created, job.completed, etc.")
    occurred_at: datetime
    resource_type: str
    resource_id: str
    data: dict = Field(description="Event-specific data")


# =============================================================================
# POS Webhooks (Toast, Clover, Square) - see EP-008
# =============================================================================


class POSWebhookPayload(BaseModel):
    """Generic POS webhook payload - will be specialized per provider in EP-008."""

    provider: str  # "toast", "clover", or "square"
    event_type: str
    occurred_at: datetime
    data: dict
