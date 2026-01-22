"""Cloudflare DNS configuration."""

from typing import Any

import pulumi
import pulumi_cloudflare as cloudflare


def create_dns_records(env: str, server_ip: pulumi.Output[str]) -> dict[str, Any]:
    """Create DNS records pointing to infrastructure.

    Args:
        env: Environment name (dev, prod)
        server_ip: IPv4 address of the Django server

    Returns:
        Dictionary of created DNS records
    """
    config = pulumi.Config()
    zone_id = config.require("cloudflare_zone_id")

    records: dict[str, Any] = {}

    # Subdomain prefix for non-prod environments
    prefix = "" if env == "prod" else f"{env}."

    # API subdomain (Django backend)
    api_record = cloudflare.Record(
        f"consult-{env}-api-dns",
        zone_id=zone_id,
        name=f"{prefix}api",
        content=server_ip,
        type="A",
        proxied=True,  # Enable Cloudflare proxy for DDoS protection
        ttl=1,  # Auto TTL when proxied
        comment=f"Consult {env} API server",
    )
    records["api"] = api_record

    # Dashboard subdomain (Django admin/dashboard)
    dashboard_record = cloudflare.Record(
        f"consult-{env}-dashboard-dns",
        zone_id=zone_id,
        name=f"{prefix}dashboard",
        content=server_ip,
        type="A",
        proxied=True,
        ttl=1,
        comment=f"Consult {env} dashboard",
    )
    records["dashboard"] = dashboard_record

    # Intake worker subdomain (CNAME to workers.dev)
    worker_name = "consult-intake" if env == "prod" else f"consult-intake-{env}"
    intake_record = cloudflare.Record(
        f"consult-{env}-intake-dns",
        zone_id=zone_id,
        name=f"{prefix}intake",
        content=f"{worker_name}.workers.dev",
        type="CNAME",
        proxied=True,
        ttl=1,
        comment=f"Consult {env} intake worker",
    )
    records["intake"] = intake_record

    return records
