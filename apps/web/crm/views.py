"""
CRM views - HTMX partials for contacts and jobs.

Full page views return complete HTML on initial load.
HTMX requests return just the partial fragments.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.web.inbox.models import Contact

from .models import Job, Note


@login_required
@require_GET
def contact_list(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/crm/contacts/

    Returns contact list with search.
    - Full page on initial load (non-HTMX)
    - Just the list partial on HTMX requests
    """
    contacts = Contact.objects.for_client(request).order_by("-last_message_at", "name")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        contacts = contacts.filter(
            Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    context = {
        "contacts": contacts,
        "search_query": search_query,
        "contact_count": Contact.objects.for_client(request).count(),
    }

    # Return partial for HTMX requests, full page otherwise
    if request.headers.get("HX-Request"):
        return render(request, "crm/partials/contact_list_items.html", context)

    return render(request, "crm/contact_list.html", context)


@login_required
@require_GET
def contact_detail(request: HttpRequest, contact_id: int) -> HttpResponse:
    """
    GET /dashboard/crm/contacts/{contact_id}/

    Returns contact detail with messages and jobs.
    """
    contact = get_object_or_404(
        Contact.objects.for_client(request).prefetch_related(
            "messages", "jobs", "notes", "notes__author", "tags"
        ),
        id=contact_id,
    )
    return render(request, "crm/contact_detail.html", {"contact": contact})


@login_required
@require_GET
def contact_info(request: HttpRequest, contact_id: int) -> HttpResponse:
    """
    GET /dashboard/crm/contacts/{contact_id}/info/

    Returns contact info partial (for canceling edit).
    """
    contact = get_object_or_404(
        Contact.objects.for_client(request),
        id=contact_id,
    )
    return render(request, "crm/partials/contact_info.html", {"contact": contact})


@login_required
@require_http_methods(["GET", "POST"])
def contact_edit(request: HttpRequest, contact_id: int) -> HttpResponse:
    """
    GET/POST /dashboard/crm/contacts/{contact_id}/edit/

    GET: Returns edit form partial.
    POST: Updates contact and returns info partial.
    """
    contact = get_object_or_404(
        Contact.objects.for_client(request),
        id=contact_id,
    )

    if request.method == "POST":
        # Update contact fields
        contact.name = request.POST.get("name", contact.name).strip()
        contact.email = request.POST.get("email", "").strip()
        contact.phone = request.POST.get("phone", "").strip()
        contact.address = request.POST.get("address", "").strip()
        contact.save(update_fields=["name", "email", "phone", "address", "updated_at"])

        return render(request, "crm/partials/contact_info.html", {"contact": contact})

    return render(request, "crm/partials/contact_edit_form.html", {"contact": contact})


@login_required
@require_POST
def add_note(request: HttpRequest, contact_id: int) -> HttpResponse:
    """
    POST /dashboard/crm/contacts/{contact_id}/notes/

    Add a note to a contact.
    """
    contact = get_object_or_404(
        Contact.objects.for_client(request),
        id=contact_id,
    )

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponse("Note content is required", status=400)

    note = Note.objects.create(
        client=request.client,  # type: ignore[attr-defined]
        contact=contact,
        content=content,
        author=request.user,
    )

    # Return the new note item partial
    # Also include script to remove "no notes" message if present
    response = render(request, "crm/partials/note_item.html", {"note": note})
    response["HX-Trigger"] = "noteAdded"
    return response


@login_required
@require_GET
def job_list(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/crm/jobs/

    Returns job list.
    """
    jobs = Job.objects.for_client(request).select_related("contact")

    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status)

    return render(request, "crm/partials/job_list.html", {"jobs": jobs})


@login_required
@require_GET
def job_detail(request: HttpRequest, job_id: int) -> HttpResponse:
    """
    GET /dashboard/crm/jobs/{job_id}/

    Returns job detail.
    """
    job = get_object_or_404(
        Job.objects.for_client(request).select_related("contact"),
        id=job_id,
    )
    return render(request, "crm/partials/job_detail.html", {"job": job})
