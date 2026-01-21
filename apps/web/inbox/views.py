"""
Inbox views - HTMX partials for dashboard.

All views return HTML fragments for HTMX swap.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Message


def inbox_list(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/inbox/

    Returns inbox message list.
    Supports filtering via query params:
    - status: unread, read, replied, archived
    - urgency: low, medium, high, urgent
    - channel: form, sms, voicemail, email
    """
    messages = Message.objects.for_client(request).select_related("contact")

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

    return render(request, "inbox/partials/message_list.html", {"messages": messages})


def message_detail(request: HttpRequest, message_id: int) -> HttpResponse:
    """
    GET /dashboard/inbox/{message_id}/

    Returns message detail panel.
    """
    message = get_object_or_404(
        Message.objects.for_client(request).select_related("contact"),
        id=message_id,
    )
    return render(request, "inbox/partials/message_detail.html", {"message": message})


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
