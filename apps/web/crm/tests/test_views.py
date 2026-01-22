"""
Tests for CRM views.
"""

from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient
from django.urls import reverse

import pytest

from apps.web.core.models import Client as ClientModel
from apps.web.crm.models import Note
from apps.web.inbox.tests.factories import ContactFactory, MessageFactory

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
class TestContactListView:
    """Tests for the contact list view."""

    def test_contact_list_requires_authentication(self):
        """Contact list should redirect anonymous users to login."""
        http_client = DjangoTestClient()
        response = http_client.get(reverse("crm:contact_list"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_contact_list_renders_for_authenticated_user(self, user, client_tenant):
        """Contact list should render for authenticated users."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_list"))
        assert response.status_code == 200
        assert b"Contacts" in response.content

    def test_contact_list_shows_contacts(self, user, client_tenant):
        """Contact list should display contacts for the client."""
        ContactFactory(client=client_tenant, name="John Doe")

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_list"))

        assert response.status_code == 200
        assert b"John Doe" in response.content

    def test_contact_list_hides_other_client_contacts(self, user, client_tenant):
        """Contact list should not show contacts from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        ContactFactory(client=other_client, name="Secret Contact")

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_list"))

        assert response.status_code == 200
        assert b"Secret Contact" not in response.content

    def test_contact_list_search_by_name(self, user, client_tenant):
        """Contact list should filter by name search."""
        ContactFactory(client=client_tenant, name="Alice Smith")
        ContactFactory(client=client_tenant, name="Bob Jones")

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_list") + "?q=Alice")

        assert response.status_code == 200
        assert b"Alice Smith" in response.content
        assert b"Bob Jones" not in response.content

    def test_contact_list_search_by_email(self, user, client_tenant):
        """Contact list should filter by email search."""
        ContactFactory(
            client=client_tenant, name="Alice", email="alice@example.com"
        )
        ContactFactory(client=client_tenant, name="Bob", email="bob@other.com")

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_list") + "?q=example.com")

        assert response.status_code == 200
        assert b"Alice" in response.content

    def test_contact_list_htmx_returns_partial(self, user, client_tenant):
        """HTMX requests should return just the list partial."""
        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(
            reverse("crm:contact_list"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" not in response.content
        assert b'id="contact-list"' in response.content


@pytest.mark.django_db
class TestContactDetailView:
    """Tests for the contact detail view."""

    def test_contact_detail_requires_authentication(self, client_tenant):
        """Contact detail should redirect anonymous users."""
        contact = ContactFactory(client=client_tenant)

        http_client = DjangoTestClient()
        response = http_client.get(reverse("crm:contact_detail", args=[contact.id]))
        assert response.status_code == 302
        assert "login" in response.url

    def test_contact_detail_renders_contact(self, user, client_tenant):
        """Contact detail should render the contact info."""
        contact = ContactFactory(
            client=client_tenant,
            name="Jane Doe",
            email="jane@example.com",
            phone="555-1234",
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_detail", args=[contact.id]))

        assert response.status_code == 200
        assert b"Jane Doe" in response.content
        assert b"jane@example.com" in response.content
        assert b"555-1234" in response.content

    def test_contact_detail_shows_messages(self, user, client_tenant):
        """Contact detail should show messages from the contact."""
        contact = ContactFactory(client=client_tenant)
        MessageFactory(
            client=client_tenant,
            contact=contact,
            body="Hello from the contact",
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_detail", args=[contact.id]))

        assert response.status_code == 200
        assert b"Hello from the contact" in response.content

    def test_contact_detail_denies_other_client_contact(self, user, client_tenant):
        """Cannot view contacts from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(
            reverse("crm:contact_detail", args=[other_contact.id])
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestContactEditView:
    """Tests for the contact edit view."""

    def test_contact_edit_get_returns_form(self, user, client_tenant):
        """GET should return the edit form."""
        contact = ContactFactory(client=client_tenant, name="Original Name")

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.get(reverse("crm:contact_edit", args=[contact.id]))

        assert response.status_code == 200
        assert b"Original Name" in response.content
        assert b'name="name"' in response.content

    def test_contact_edit_post_updates_contact(self, user, client_tenant):
        """POST should update the contact."""
        contact = ContactFactory(
            client=client_tenant,
            name="Old Name",
            email="old@example.com",
        )

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("crm:contact_edit", args=[contact.id]),
            {
                "name": "New Name",
                "email": "new@example.com",
                "phone": "555-9999",
                "address": "123 New St",
            },
        )

        assert response.status_code == 200
        contact.refresh_from_db()
        assert contact.name == "New Name"
        assert contact.email == "new@example.com"
        assert contact.phone == "555-9999"
        assert contact.address == "123 New St"

    def test_contact_edit_denies_other_client_contact(self, user, client_tenant):
        """Cannot edit contacts from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("crm:contact_edit", args=[other_contact.id]),
            {"name": "Hacked Name"},
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestAddNoteView:
    """Tests for the add note view."""

    def test_add_note_creates_note(self, user, client_tenant):
        """Should create a note on the contact."""
        contact = ContactFactory(client=client_tenant)

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("crm:add_note", args=[contact.id]),
            {"content": "This is a test note"},
        )

        assert response.status_code == 200
        assert Note.objects.filter(contact=contact).exists()
        note = Note.objects.get(contact=contact)
        assert note.content == "This is a test note"
        assert note.author == user

    def test_add_note_requires_content(self, user, client_tenant):
        """Note content is required."""
        contact = ContactFactory(client=client_tenant)

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("crm:add_note", args=[contact.id]),
            {"content": ""},
        )

        assert response.status_code == 400
        assert not Note.objects.filter(contact=contact).exists()

    def test_add_note_denies_other_client_contact(self, user, client_tenant):
        """Cannot add notes to contacts from other clients."""
        other_client = ClientModel.objects.create(
            slug="other-client",
            name="Other Client",
            email="other@example.com",
        )
        other_contact = ContactFactory(client=other_client)

        http_client = DjangoTestClient()
        http_client.force_login(user)
        response = http_client.post(
            reverse("crm:add_note", args=[other_contact.id]),
            {"content": "Sneaky note"},
        )

        assert response.status_code == 404
        assert not Note.objects.filter(contact=other_contact).exists()
