"""
CRM views - HTMX partials for contacts and jobs.
"""

from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.web.inbox.models import Contact

from .models import Job


def contact_list(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/crm/contacts/

    Returns contact list with search.
    """
    contacts = Contact.objects.for_client(request)

    q = request.GET.get("q", "").strip()
    if q:
        contacts = contacts.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    return render(request, "crm/partials/contact_list.html", {"contacts": contacts})


def contact_detail(request: HttpRequest, contact_id: int) -> HttpResponse:
    """
    GET /dashboard/crm/contacts/{contact_id}/

    Returns contact detail with messages and jobs.
    """
    contact = get_object_or_404(
        Contact.objects.for_client(request).prefetch_related("messages", "jobs"),
        id=contact_id,
    )
    return render(request, "crm/partials/contact_detail.html", {"contact": contact})


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
