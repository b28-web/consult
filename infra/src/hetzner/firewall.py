"""Hetzner firewall rules for secure server access."""

import pulumi
import pulumi_hcloud as hcloud

# Cloudflare IPv4 ranges
# Source: https://www.cloudflare.com/ips-v4
CLOUDFLARE_IPV4 = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
]

# Cloudflare IPv6 ranges
# Source: https://www.cloudflare.com/ips-v6
CLOUDFLARE_IPV6 = [
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
]

CLOUDFLARE_IPS = CLOUDFLARE_IPV4 + CLOUDFLARE_IPV6


def create_firewall(env: str) -> hcloud.Firewall:
    """Create firewall with strict security rules.

    - SSH: Restricted to admin IPs only (configured via Pulumi config)
    - HTTP/HTTPS: Only from Cloudflare IPs (traffic must go through CF proxy)
    - Django dev port: Only in dev environment

    Args:
        env: Environment name (dev, prod)

    Returns:
        The created Hetzner firewall
    """
    config = pulumi.Config()

    # Admin IPs for SSH access - defaults to allow all in dev, none in prod
    admin_ssh_ips = config.get_object("admin_ssh_ips")
    if admin_ssh_ips is None:
        # Dev: allow from anywhere for convenience; Prod: must be explicitly configured
        admin_ssh_ips = ["0.0.0.0/0", "::/0"] if env == "dev" else []

    rules: list[hcloud.FirewallRuleArgs] = []

    # SSH access (restricted)
    if admin_ssh_ips:
        rules.append(
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="22",
                source_ips=admin_ssh_ips,
                description="SSH from admin IPs",
            )
        )

    # HTTP from Cloudflare only
    rules.append(
        hcloud.FirewallRuleArgs(
            direction="in",
            protocol="tcp",
            port="80",
            source_ips=CLOUDFLARE_IPS,
            description="HTTP from Cloudflare",
        )
    )

    # HTTPS from Cloudflare only
    rules.append(
        hcloud.FirewallRuleArgs(
            direction="in",
            protocol="tcp",
            port="443",
            source_ips=CLOUDFLARE_IPS,
            description="HTTPS from Cloudflare",
        )
    )

    # Django dev server port (only in dev, from anywhere for testing)
    if env == "dev":
        rules.append(
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="8000",
                source_ips=["0.0.0.0/0", "::/0"],
                description="Django dev server",
            )
        )

    return hcloud.Firewall(
        f"consult-{env}-firewall",
        name=f"consult-{env}",
        rules=rules,
        labels={
            "environment": env,
            "managed_by": "pulumi",
        },
    )
