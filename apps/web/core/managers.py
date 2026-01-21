"""
Custom managers for multi-tenancy.

ClientScopedManager filters queries by the current client.
"""

from typing import TYPE_CHECKING, Any, TypeVar

from django.db import models

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .models import ClientScopedModel

_T = TypeVar("_T", bound="ClientScopedModel")


class ClientScopedManager(models.Manager[_T]):
    """
    Manager that filters by client.

    Usage in views:
        # Automatically scoped to request.client
        messages = Message.objects.for_client(request).all()

    SECURITY: Always use for_client() in views, never raw querysets.
    """

    def for_client(self, request: "HttpRequest") -> models.QuerySet[_T]:
        """
        Filter queryset by the client attached to the request.

        Args:
            request: HttpRequest with .client attribute (set by ClientMiddleware)

        Returns:
            QuerySet filtered to the request's client

        Raises:
            ValueError: If request has no client attached
        """
        client: Any = getattr(request, "client", None)
        if client is None:
            msg = "Request has no client attached. Is ClientMiddleware enabled?"
            raise ValueError(msg)
        return self.filter(client=client)
