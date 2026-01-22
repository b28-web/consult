"""Form submission schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ContactFormSubmission(BaseModel):
    """Standard contact form submission from Astro sites."""

    # Client identification
    client_id: str = Field(description="Client identifier from hidden field or domain")

    # Contact info
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)

    # Message
    message: str = Field(min_length=1, max_length=5000)

    # Metadata
    source_url: str | None = Field(
        default=None, description="Page URL where form was submitted"
    )
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    user_agent: str | None = None
    ip_address: str | None = None


class QuoteRequestSubmission(BaseModel):
    """Quote request form - used by hauler, cleaning, landscaper."""

    # Client identification
    client_id: str

    # Contact info
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(max_length=20)  # Required for quote requests

    # Service details
    service_type: str | None = Field(
        default=None, description="Type of service requested"
    )
    service_address: str = Field(min_length=1, max_length=500)
    preferred_date: str | None = Field(
        default=None, description="Preferred service date"
    )
    preferred_time: str | None = Field(
        default=None, description="Preferred time window"
    )

    # Additional info
    description: str = Field(min_length=1, max_length=5000)
    photos: list[str] = Field(
        default_factory=list, description="URLs to uploaded photos"
    )

    # Metadata
    source_url: str | None = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
