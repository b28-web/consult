"""
Decorators for request handling and validation.
"""

import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse


def idempotency_key_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that requires an Idempotency-Key header for POST requests.

    If the same key is used twice, returns the cached response from the first request.
    Cached responses are stored for 24 hours.

    Usage:
        @idempotency_key_required
        def create_order(request, slug):
            ...
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        key = request.headers.get("Idempotency-Key")

        if not key:
            return JsonResponse(
                {"error": "Idempotency-Key header is required"},
                status=400,
            )

        cache_key = f"idempotency:{key}"
        cached = cache.get(cache_key)

        if cached:
            # Return cached response
            return JsonResponse(
                cached["data"],
                status=cached["status"],
            )

        # Call the actual view
        response = view_func(request, *args, **kwargs)

        # Cache successful responses for 24 hours
        if response.status_code < 400:
            cache.set(
                cache_key,
                {
                    "data": json.loads(response.content),
                    "status": response.status_code,
                },
                timeout=86400,  # 24 hours
            )

        return response

    return wrapper
