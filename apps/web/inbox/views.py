"""
Inbox views - HTMX partials for dashboard.

Full page views return complete HTML on initial load.
HTMX requests return just the partial fragments.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Message

# Urgency ordering: urgent=0, high=1, medium=2, low=3, empty=4
URGENCY_ORDER = Case(
    When(urgency="urgent", then=Value(0)),
    When(urgency="high", then=Value(1)),
    When(urgency="medium", then=Value(2)),
    When(urgency="low", then=Value(3)),
    default=Value(4),
    output_field=IntegerField(),
)


@login_required
def inbox_list(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/inbox/

    Returns inbox message list.
    - Full page on initial load (non-HTMX)
    - Just the message list partial on HTMX requests

    Supports filtering via query params:
    - status: unread, read, replied, archived
    - urgency: low, medium, high, urgent
    - channel: form, sms, voicemail, email
    """
    messages = (
        Message.objects.for_client(request)
        .filter(direction=Message.Direction.INBOUND)
        .select_related("contact")
        .annotate(urgency_order=URGENCY_ORDER)
        .order_by("urgency_order", "-received_at")
    )

    # Filters
    status = request.GET.get("status")
    if status:
        messages = messages.filter(status=status)

    urgency = request.GET.get("urgency")
    if urgency:
        messages = messages.filter(urgency=urgency)

    channel = request.GET.get("channel")
    if channel:
        messages = messages.filter(channel=channel)

    # Unread count for badge
    unread_count = (
        Message.objects.for_client(request)
        .filter(direction=Message.Direction.INBOUND, status=Message.Status.UNREAD)
        .count()
    )

    context = {
        "messages": messages,
        "unread_count": unread_count,
        "current_status": status,
        "current_channel": channel,
        "current_urgency": urgency,
    }

    # Return partial for HTMX requests, full page otherwise
    if request.headers.get("HX-Request"):
        return render(request, "inbox/partials/message_list.html", context)

    return render(request, "inbox/inbox.html", context)


@login_required
def message_detail(request: HttpRequest, message_id: int) -> HttpResponse:
    """
    GET /dashboard/inbox/{message_id}/

    Returns message detail panel with contact history.
    """
    message = get_object_or_404(
        Message.objects.for_client(request).select_related("contact"),
        id=message_id,
    )

    # Get contact history (other messages from same contact, excluding current)
    contact_history = (
        Message.objects.for_client(request)
        .filter(contact=message.contact)
        .exclude(id=message_id)
        .order_by("-received_at")[:5]
    )

    return render(
        request,
        "inbox/partials/message_detail.html",
        {
            "message": message,
            "contact_history": contact_history,
        },
    )


@login_required
def message_reply(request: HttpRequest, message_id: int) -> HttpResponse:
    """
    POST /dashboard/inbox/{message_id}/reply/

    Send a reply to a message.
    """
    message = get_object_or_404(
        Message.objects.for_client(request),
        id=message_id,
    )

    if request.method != "POST":
        return HttpResponse(status=405)

    body = request.POST.get("body", "").strip()
    channel = request.POST.get("channel", message.channel)

    if not body:
        return render(
            request,
            "inbox/partials/reply_error.html",
            {"error": "Reply body is required"},
        )

    # TODO: Actually send via Mailgun/Twilio
    # For now, just create the outbound message record
    _reply = Message.objects.create(
        client=request.client,  # type: ignore[attr-defined]
        contact=message.contact,
        channel=channel,
        direction=Message.Direction.OUTBOUND,
        status=Message.Status.READ,
        body=body,
    )

    # Mark original as replied
    message.status = Message.Status.REPLIED
    message.save(update_fields=["status"])

    return render(
        request,
        "inbox/partials/reply_success.html",
        {"message": message},
    )


@login_required
def message_mark(request: HttpRequest, message_id: int) -> HttpResponse:
    """
    POST /dashboard/inbox/{message_id}/mark/

    Mark message as read/archived.
    """
    message = get_object_or_404(
        Message.objects.for_client(request),
        id=message_id,
    )

    if request.method != "POST":
        return HttpResponse(status=405)

    new_status = request.POST.get("status")
    if new_status not in [Message.Status.READ, Message.Status.ARCHIVED]:
        return HttpResponse("Invalid status", status=400)

    message.status = new_status
    message.save(update_fields=["status"])

    return render(
        request,
        "inbox/partials/message_row.html",
        {"message": message},
    )
