"""
Integrations models - External service connections.

Stores OAuth tokens and configuration for third-party integrations
like Jobber and Cal.com.
"""

from datetime import UTC

from django.db import models

from apps.web.core.models import ClientScopedModel


class Integration(ClientScopedModel):
    """
    OAuth/API integration with an external service.

    Stores credentials encrypted, tracks connection status.
    """

    class Provider(models.TextChoices):
        JOBBER = "jobber", "Jobber"
        CALCOM = "calcom", "Cal.com"

    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
    )

    # OAuth credentials (access_token, refresh_token, expires_at)
    credentials = models.JSONField(default=dict, blank=True)

    # Webhook secret for receiving webhooks from this provider
    webhook_secret = models.CharField(max_length=100, blank=True)

    # Connection status
    is_active = models.BooleanField(default=True)

    # External account identifier (for display purposes)
    external_account_id = models.CharField(max_length=100, blank=True)
    external_account_name = models.CharField(max_length=200, blank=True)

    # Connection metadata
    connected_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "provider"],
                name="unique_integration_per_client_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider} integration for {self.client}"

    @property
    def is_token_expired(self) -> bool:
        """Check if OAuth token has expired."""
        from datetime import datetime  # noqa: PLC0415

        expires_at = self.credentials.get("expires_at")
        if not expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at)
            return datetime.now(UTC) > expiry
        except (ValueError, TypeError):
            return True

    def get_access_token(self) -> str | None:
        """Get access token, returning None if not set."""
        token = self.credentials.get("access_token")
        return str(token) if token else None
