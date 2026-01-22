"""
Dashboard views - Authentication and main shell.
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.web.inbox.models import Message


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    GET/POST /dashboard/login/

    Login page with email/password form.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "dashboard:home")
            # Prevent open redirect
            if not next_url.startswith("/"):
                next_url = "dashboard:home"
            return redirect(next_url)
        else:
            error = "Invalid username or password"

    return render(request, "dashboard/login.html", {"error": error})


@require_GET
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/logout/

    Logout and redirect to login page.
    """
    logout(request)
    return redirect("dashboard:login")


@login_required
@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """
    GET /dashboard/

    Dashboard home page - shows overview and quick stats.
    """
    # Get unread message count for sidebar badge
    unread_count = 0
    if hasattr(request, "client") and request.client:
        unread_count = Message.objects.filter(
            client=request.client,
            status=Message.Status.UNREAD,
        ).count()

    return render(
        request,
        "dashboard/home.html",
        {
            "unread_count": unread_count,
        },
    )
