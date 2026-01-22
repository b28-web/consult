"""Cloudflare Workers for edge functions."""

from typing import Any

import pulumi
import pulumi_cloudflare as cloudflare


def create_workers(env: str) -> dict[str, Any]:
    """Create Cloudflare Workers infrastructure.

    Note: Worker code is deployed via `wrangler deploy` in CI/CD.
    This sets up the worker configuration and bindings.

    Args:
        env: Environment name (dev, prod)

    Returns:
        Dictionary of worker resources
    """
    config = pulumi.Config()
    zone_id = config.require("cloudflare_zone_id")
    domain = config.require("domain")

    workers: dict[str, Any] = {}

    # Intake worker - handles form submissions
    worker_name = "consult-intake" if env == "prod" else f"consult-intake-{env}"

    # Note: The actual worker script is deployed via wrangler
    # This creates a placeholder that wrangler will update
    # We just set up the route here

    # Subdomain prefix for non-prod
    prefix = "" if env == "prod" else f"{env}."

    # Worker route
    route = cloudflare.WorkerRoute(
        f"consult-{env}-intake-route",
        zone_id=zone_id,
        pattern=f"{prefix}intake.{domain}/*",
        script_name=worker_name,
    )

    workers["intake"] = {
        "name": worker_name,
        "route": route,
    }

    return workers
