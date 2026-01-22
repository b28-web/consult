"""
Integration views for OAuth flows.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

import httpx

from apps.web.integrations.models import Integration

logger = logging.getLogger(__name__)

JOBBER_AUTHORIZE_URL = "https://api.getjobber.com/api/oauth/authorize"
JOBBER_TOKEN_URL = "https://api.getjobber.com/api/oauth/token"
JOBBER_API_URL = "https://api.getjobber.com/api/graphql"


@login_required
def jobber_authorize(request: HttpRequest) -> HttpResponse:
    """Redirect user to Jobber OAuth authorization page."""
    if not settings.JOBBER_CLIENT_ID:
        messages.error(request, "Jobber integration is not configured.")
        return redirect("dashboard:settings")

    # Build OAuth authorization URL
    params = {
        "client_id": settings.JOBBER_CLIENT_ID,
        "redirect_uri": request.build_absolute_uri(
            reverse("integrations:jobber_callback")
        ),
        "response_type": "code",
    }

    auth_url = f"{JOBBER_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(auth_url)


@login_required
def jobber_callback(request: HttpRequest) -> HttpResponse:
    """Handle OAuth callback from Jobber."""
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        messages.error(request, f"Jobber authorization failed: {error_description}")
        return redirect("dashboard:settings")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "No authorization code received from Jobber.")
        return redirect("dashboard:settings")

    # Exchange code for tokens
    try:
        tokens = exchange_jobber_code(request, code)
    except JobberOAuthError as e:
        logger.exception("Jobber OAuth error: %s", e)
        messages.error(request, f"Failed to connect Jobber: {e}")
        return redirect("dashboard:settings")

    # Get account info
    try:
        account_info = get_jobber_account_info(tokens["access_token"])
    except JobberAPIError as e:
        logger.warning("Failed to get Jobber account info: %s", e)
        account_info = {"id": "", "name": "Unknown"}

    # Store integration
    client = request.client  # type: ignore[attr-defined]
    integration, created = Integration.objects.update_or_create(
        client=client,
        provider=Integration.Provider.JOBBER,
        defaults={
            "credentials": tokens,
            "is_active": True,
            "external_account_id": account_info.get("id", ""),
            "external_account_name": account_info.get("name", ""),
        },
    )

    action = "Connected" if created else "Reconnected"
    messages.success(request, f"{action} to Jobber successfully!")
    logger.info(
        "%s Jobber integration for client %s (account: %s)",
        action,
        client.id,
        integration.external_account_name,
    )

    return redirect("dashboard:settings")


@login_required
def jobber_disconnect(request: HttpRequest) -> HttpResponse:
    """Disconnect Jobber integration."""
    if request.method != "POST":
        return redirect("dashboard:settings")

    client = request.client  # type: ignore[attr-defined]
    integration = Integration.objects.filter(
        client=client,
        provider=Integration.Provider.JOBBER,
    ).first()

    if integration:
        integration.is_active = False
        integration.credentials = {}
        integration.save(update_fields=["is_active", "credentials"])
        messages.success(request, "Disconnected from Jobber.")
        logger.info("Disconnected Jobber integration for client %s", client.id)
    else:
        messages.info(request, "No Jobber connection found.")

    return redirect("dashboard:settings")


class JobberOAuthError(Exception):
    """Error during Jobber OAuth flow."""

    pass


class JobberAPIError(Exception):
    """Error calling Jobber API."""

    pass


def exchange_jobber_code(request: HttpRequest, code: str) -> dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    data = {
        "client_id": settings.JOBBER_CLIENT_ID,
        "client_secret": settings.JOBBER_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": request.build_absolute_uri(
            reverse("integrations:jobber_callback")
        ),
    }

    with httpx.Client() as client:
        response = client.post(JOBBER_TOKEN_URL, data=data)

    if response.status_code != 200:
        raise JobberOAuthError(f"Token exchange failed: {response.text}")

    result = response.json()

    # Calculate expiry time
    expires_in = result.get("expires_in", 3600)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    return {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "expires_at": expires_at.isoformat(),
        "token_type": result.get("token_type", "Bearer"),
    }


def refresh_jobber_token(integration: Integration) -> dict[str, Any]:
    """Refresh expired access token using refresh token."""
    refresh_token = integration.credentials.get("refresh_token")
    if not refresh_token:
        raise JobberOAuthError("No refresh token available")

    data = {
        "client_id": settings.JOBBER_CLIENT_ID,
        "client_secret": settings.JOBBER_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    with httpx.Client() as client:
        response = client.post(JOBBER_TOKEN_URL, data=data)

    if response.status_code != 200:
        raise JobberOAuthError(f"Token refresh failed: {response.text}")

    result = response.json()

    # Calculate expiry time
    expires_in = result.get("expires_in", 3600)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    tokens = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", refresh_token),
        "expires_at": expires_at.isoformat(),
        "token_type": result.get("token_type", "Bearer"),
    }

    # Update integration with new tokens
    integration.credentials = tokens
    integration.save(update_fields=["credentials"])

    logger.info("Refreshed Jobber token for client %s", integration.client_id)
    return tokens


def get_valid_jobber_token(integration: Integration) -> str:
    """Get valid access token, refreshing if needed."""
    if integration.is_token_expired:
        tokens = refresh_jobber_token(integration)
        return str(tokens["access_token"])
    return str(integration.credentials.get("access_token", ""))


def get_jobber_account_info(access_token: str) -> dict[str, Any]:
    """Get Jobber account information via GraphQL API."""
    query = """
    query {
        account {
            id
            name
        }
    }
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": "2024-01-18",
    }

    with httpx.Client() as client:
        response = client.post(
            JOBBER_API_URL,
            headers=headers,
            json={"query": query},
        )

    if response.status_code != 200:
        raise JobberAPIError(f"API request failed: {response.text}")

    result = response.json()

    if "errors" in result:
        raise JobberAPIError(f"GraphQL errors: {result['errors']}")

    account = result.get("data", {}).get("account", {})
    return {
        "id": account.get("id", ""),
        "name": account.get("name", ""),
    }
