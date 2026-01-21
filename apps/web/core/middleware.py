"""
Client middleware - attaches current client to request.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.http import Http404, HttpRequest, HttpResponse

if TYPE_CHECKING:
    from .models import Client


class ClientMiddleware:
    """
    Middleware that attaches the current client to the request.

    Client is determined by (in order):
    1. X-Client-ID header (for API/worker calls)
    2. Subdomain (client.consult.io)
    3. User's assigned client (for dashboard)

    Sets request.client or raises 404 if client not found.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip for admin
        if request.path.startswith("/admin/"):
            return self.get_response(request)

        client = self._get_client(request)
        if client is None and request.path.startswith("/dashboard/"):
            raise Http404("Client not found")

        request.client = client  # type: ignore[attr-defined]
        return self.get_response(request)

    def _get_client(self, request: HttpRequest) -> "Client | None":
        """Resolve client from request."""
        # Lazy import to avoid circular dependency
        from .models import Client

        # 1. Header (for API calls)
        client_id = request.headers.get("X-Client-ID")
        if client_id:
            try:
                return Client.objects.get(slug=client_id, is_active=True)
            except Client.DoesNotExist:
                return None

        # 2. Subdomain
        host = request.get_host().split(":")[0]  # Remove port
        if "." in host:
            subdomain = host.split(".")[0]
            try:
                return Client.objects.get(slug=subdomain, is_active=True)
            except Client.DoesNotExist:
                pass

        # 3. User's client
        if request.user.is_authenticated:
            return getattr(request.user, "client", None)

        return None
