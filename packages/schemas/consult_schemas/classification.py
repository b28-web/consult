"""Classification schemas - mirrors BAML types."""

from enum import Enum

from pydantic import BaseModel, Field


class MessageCategory(str, Enum):
    """Category of incoming message."""

    QUOTE_REQUEST = "QUOTE_REQUEST"
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    COMPLAINT = "COMPLAINT"
    FOLLOW_UP = "FOLLOW_UP"
    SPAM = "SPAM"
    OTHER = "OTHER"


class MessageIntent(str, Enum):
    """Detected intent of the message sender."""

    WANTS_SERVICE = "WANTS_SERVICE"
    WANTS_INFORMATION = "WANTS_INFORMATION"
    WANTS_STATUS_UPDATE = "WANTS_STATUS_UPDATE"
    WANTS_TO_CANCEL = "WANTS_TO_CANCEL"
    WANTS_TO_RESCHEDULE = "WANTS_TO_RESCHEDULE"
    PROVIDING_FEEDBACK = "PROVIDING_FEEDBACK"
    OTHER = "OTHER"


class SuggestedAction(str, Enum):
    """Recommended action for handling the message."""

    RESPOND_URGENTLY = "RESPOND_URGENTLY"
    SCHEDULE_CALLBACK = "SCHEDULE_CALLBACK"
    SEND_QUOTE = "SEND_QUOTE"
    BOOK_APPOINTMENT = "BOOK_APPOINTMENT"
    FORWARD_TO_OWNER = "FORWARD_TO_OWNER"
    AUTO_REPLY = "AUTO_REPLY"
    MARK_AS_SPAM = "MARK_AS_SPAM"
    NO_ACTION_NEEDED = "NO_ACTION_NEEDED"


class MessageClassification(BaseModel):
    """AI classification result for an incoming message."""

    is_new_lead: bool = Field(
        description="True if this appears to be a new potential customer"
    )
    urgency: int = Field(ge=1, le=5, description="1-5 scale, 5 being most urgent")
    category: MessageCategory
    intent: MessageIntent
    suggested_action: SuggestedAction
    summary: str = Field(description="One sentence summary of the message")
    extracted_name: str | None = Field(
        default=None, description="Contact name if mentioned"
    )
    extracted_phone: str | None = Field(
        default=None, description="Phone number if mentioned"
    )
    extracted_email: str | None = Field(default=None, description="Email if mentioned")
    extracted_address: str | None = Field(
        default=None, description="Service address if mentioned"
    )
    confidence: float = Field(
        ge=0, le=1, description="0-1 confidence score for this classification"
    )
