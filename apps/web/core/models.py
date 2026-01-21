"""
Core models - Multi-tenancy foundation.

All tenant-scoped models inherit from ClientScopedModel.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import ClientScopedManager


class Client(models.Model):
    """
    Tenant - represents a business client.

    All data is scoped to a Client.
    """

    slug = models.SlugField(unique=True, help_text="URL-safe identifier")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # Site configuration
    site_url = models.URLField(blank=True, help_text="Astro site URL")
    intake_url = models.URLField(blank=True, help_text="Worker intake endpoint")

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Custom user model with client association.

    Users belong to one Client (staff) or none (superuser).
    """

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        help_text="Null for superusers",
    )

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        STAFF = "staff", "Staff"
        READONLY = "readonly", "Read Only"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        if self.client:
            return f"{self.username} ({self.client.slug})"
        return self.username


class ClientScopedModel(models.Model):
    """
    Abstract base for all tenant-scoped models.

    Provides:
    - Automatic client FK
    - ClientScopedManager for filtered queries
    - Created/updated timestamps
    """

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="%(class)ss",  # e.g., client.contacts, client.messages
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ClientScopedManager()

    class Meta:
        abstract = True
