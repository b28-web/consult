"""POS integration exceptions."""


class POSError(Exception):
    """Base exception for POS integration errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.message = message
        self.provider = provider
        super().__init__(message)


class POSAuthError(POSError):
    """Authentication failed with POS provider."""


class POSAPIError(POSError):
    """API request to POS provider failed."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.status_code = status_code
        self.response_body = response_body


class POSWebhookError(POSError):
    """Webhook validation or processing failed."""


class POSOrderError(POSError):
    """Order creation or processing failed."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        order_id: str | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.order_id = order_id


class POSRateLimitError(POSAPIError):
    """Rate limit exceeded with POS provider."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.retry_after = retry_after
