"""
Pytest configuration for Django app tests.
"""

from django.contrib.auth import get_user_model

import pytest

from apps.web.core.models import Client


@pytest.fixture
def client_tenant() -> Client:
    """Create a test client (tenant)."""
    return Client.objects.create(
        slug="test-client",
        name="Test Client",
        email="test@example.com",
    )


@pytest.fixture
def user(client_tenant: Client) -> get_user_model():
    """Create a test user associated with the client tenant."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        client=client_tenant,
    )
