"""
Tests for dashboard views.
"""

from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient
from django.urls import reverse

import pytest

from apps.web.core.models import Client as ClientModel

User = get_user_model()


@pytest.fixture
def client_tenant(db) -> ClientModel:
    """Create a test client (tenant)."""
    return ClientModel.objects.create(
        slug="test-client",
        name="Test Client",
        email="test@example.com",
    )


@pytest.fixture
def user(client_tenant: ClientModel) -> User:
    """Create a test user associated with the client tenant."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        client=client_tenant,
    )


@pytest.mark.django_db
class TestLoginView:
    """Tests for the login view."""

    def test_login_page_renders(self):
        """Login page should render for anonymous users."""
        http_client = DjangoTestClient()
        response = http_client.get(reverse("dashboard:login"))
        assert response.status_code == 200
        assert b"Sign in" in response.content

    def test_login_redirects_authenticated_user(self, user):
        """Authenticated users should be redirected to home."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("dashboard:login"))
        assert response.status_code == 302
        assert response.url == reverse("dashboard:home")

    def test_login_with_valid_credentials(self, user):
        """Valid credentials should log user in and redirect."""
        http_client = DjangoTestClient()
        response = http_client.post(
            reverse("dashboard:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == reverse("dashboard:home")

    def test_login_with_invalid_credentials(self, user):
        """Invalid credentials should show error."""
        http_client = DjangoTestClient()
        response = http_client.post(
            reverse("dashboard:login"),
            {"username": "testuser", "password": "wrongpass"},
        )
        assert response.status_code == 200
        assert b"Invalid username or password" in response.content

    def test_login_respects_next_parameter(self, user):
        """Login should redirect to 'next' URL after success."""
        http_client = DjangoTestClient()
        next_url = "/dashboard/inbox/"
        response = http_client.post(
            f"{reverse('dashboard:login')}?next={next_url}",
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == next_url


@pytest.mark.django_db
class TestLogoutView:
    """Tests for the logout view."""

    def test_logout_logs_out_user(self, user):
        """Logout should log out user and redirect to login."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("dashboard:logout"))
        assert response.status_code == 302
        assert response.url == reverse("dashboard:login")

        # Verify user is logged out
        response = http_client.get(reverse("dashboard:home"))
        assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
class TestHomeView:
    """Tests for the dashboard home view."""

    def test_home_requires_authentication(self):
        """Home page should redirect anonymous users to login."""
        http_client = DjangoTestClient()
        response = http_client.get(reverse("dashboard:home"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_home_renders_for_authenticated_user(self, user):
        """Home page should render for authenticated users."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("dashboard:home"))
        assert response.status_code == 200
        assert b"Welcome back" in response.content

    def test_home_shows_user_info(self, user):
        """Home page should display user information."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("dashboard:home"))
        assert b"testuser" in response.content
