"""Stack outputs for consumption by other tools."""

from typing import Any

import pulumi
from pulumi_hcloud import Server


def export_outputs(
    env: str,
    django_server: Server,
    dns_records: dict[str, Any],
    sites: dict[str, Any],
    intake_worker: dict[str, Any],
    security_rules: dict[str, Any],
) -> None:
    """Export stack outputs for use by deployment scripts and other tools."""
    # Environment
    pulumi.export("environment", env)

    # Django server
    pulumi.export("django_server_ip", django_server.ipv4_address)
    pulumi.export("django_server_id", django_server.id)
    pulumi.export("django_server_name", django_server.name)

    # DNS
    pulumi.export("dns_records", dns_records)

    # Sites
    pulumi.export("sites", sites)

    # Workers
    pulumi.export("intake_worker", intake_worker)

    # Security
    pulumi.export("security_rules", security_rules)
