"""
Factory classes for inbox models.
"""

import uuid
from typing import Any

from django.utils import timezone

import factory

from apps.web.core.models import Client
from apps.web.inbox.models import Contact, Message, Submission


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Client

    slug = factory.Sequence(lambda n: f"client-{n}")
    name = factory.Sequence(lambda n: f"Client {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.slug}@example.com")


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    client = factory.SubFactory(ClientFactory)
    name = factory.Faker("name")
    email = factory.Faker("email")
    phone = ""


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    client = factory.SubFactory(ClientFactory)
    contact = factory.SubFactory(
        ContactFactory, client=factory.SelfAttribute("..client")
    )
    channel = Message.Channel.FORM
    direction = Message.Direction.INBOUND
    body = factory.Faker("paragraph")


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    id = factory.LazyFunction(uuid.uuid4)
    client_slug = factory.Sequence(lambda n: f"client-{n}")
    channel = "form"
    payload: dict[str, Any] = factory.LazyAttribute(
        lambda obj: {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Hello, I have a question.",
        }
    )
    source_url = "https://example.com/contact"
    created_at = factory.LazyFunction(timezone.now)
    processed_at = None
    error = ""
    message = None
