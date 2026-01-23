"""Base POS adapter protocol - interface for all POS integrations."""

from typing import Any, Protocol, runtime_checkable

from consult_schemas import (
    POSCredentials,
    POSMenu,
    POSOrder,
    POSOrderResult,
    POSOrderStatus,
    POSProvider,
    POSSession,
    POSWebhookEvent,
)


@runtime_checkable
class POSAdapter(Protocol):
    """
    Protocol defining the interface for POS system integrations.

    All POS adapters (Toast, Clover, Square, Mock) must implement this interface.
    Methods are async to support non-blocking I/O with external APIs.
    """

    @property
    def provider(self) -> POSProvider:
        """The POS provider this adapter connects to."""
        ...

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self, credentials: POSCredentials) -> POSSession:
        """
        Authenticate with the POS provider.

        Args:
            credentials: Client credentials for the POS provider.

        Returns:
            Authenticated session with access token.

        Raises:
            POSAuthError: If authentication fails.
        """
        ...

    async def refresh_token(self, session: POSSession) -> POSSession:
        """
        Refresh an expired access token.

        Args:
            session: Current session with refresh token.

        Returns:
            New session with fresh access token.

        Raises:
            POSAuthError: If token refresh fails.
        """
        ...

    # =========================================================================
    # Menu Operations (read)
    # =========================================================================

    async def get_menus(self, session: POSSession, location_id: str) -> list[POSMenu]:
        """
        Get all menus for a location.

        Args:
            session: Authenticated session.
            location_id: POS location identifier.

        Returns:
            List of menus with categories and items.

        Raises:
            POSAPIError: If the API request fails.
            POSRateLimitError: If rate limit is exceeded.
        """
        ...

    async def get_menu(
        self, session: POSSession, location_id: str, menu_id: str
    ) -> POSMenu:
        """
        Get a specific menu by ID.

        Args:
            session: Authenticated session.
            location_id: POS location identifier.
            menu_id: Menu identifier in the POS system.

        Returns:
            The requested menu with categories and items.

        Raises:
            POSAPIError: If the API request fails or menu not found.
        """
        ...

    async def get_item_availability(
        self, session: POSSession, location_id: str
    ) -> dict[str, bool]:
        """
        Get current availability status for all items.

        Args:
            session: Authenticated session.
            location_id: POS location identifier.

        Returns:
            Dict mapping item external_id to availability (True = available).

        Raises:
            POSAPIError: If the API request fails.
        """
        ...

    # =========================================================================
    # Order Operations (write)
    # =========================================================================

    async def create_order(
        self, session: POSSession, location_id: str, order: POSOrder
    ) -> POSOrderResult:
        """
        Create a new order in the POS system.

        Args:
            session: Authenticated session.
            location_id: POS location identifier.
            order: Order details to submit.

        Returns:
            Result with POS order ID and initial status.

        Raises:
            POSOrderError: If order creation fails.
            POSAPIError: If the API request fails.
        """
        ...

    async def get_order_status(
        self, session: POSSession, location_id: str, order_id: str
    ) -> POSOrderStatus:
        """
        Get current status of an order.

        Args:
            session: Authenticated session.
            location_id: POS location identifier.
            order_id: Order ID in the POS system.

        Returns:
            Current order status.

        Raises:
            POSAPIError: If the API request fails or order not found.
        """
        ...

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """
        Verify the authenticity of a webhook payload.

        Args:
            payload: Raw webhook payload bytes.
            signature: Signature header from the webhook request.
            secret: Webhook secret for this integration.

        Returns:
            True if signature is valid, False otherwise.
        """
        ...

    def parse_webhook(self, payload: dict[str, Any]) -> POSWebhookEvent:
        """
        Parse a webhook payload into a typed event.

        Args:
            payload: Parsed JSON webhook payload.

        Returns:
            Typed webhook event (MenuUpdated, ItemAvailabilityChanged, etc.)

        Raises:
            POSWebhookError: If payload cannot be parsed.
        """
        ...
