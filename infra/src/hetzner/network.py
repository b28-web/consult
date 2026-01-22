"""Hetzner network infrastructure: VPC, subnets, and firewall rules."""

from dataclasses import dataclass

import pulumi_hcloud as hcloud


@dataclass
class NetworkResources:
    """Container for network-related resources."""

    network: hcloud.Network
    subnet: hcloud.NetworkSubnet
    firewall: hcloud.Firewall


def create_network(env: str) -> NetworkResources:
    """Create VPC network with subnet and firewall rules.

    Args:
        env: Environment name (dev, prod)

    Returns:
        NetworkResources containing network, subnet, and firewall
    """
    # Private network for internal communication
    network = hcloud.Network(
        f"consult-{env}-network",
        name=f"consult-{env}",
        ip_range="10.0.0.0/16",
    )

    # Subnet in the US West region
    subnet = hcloud.NetworkSubnet(
        f"consult-{env}-subnet",
        network_id=network.id.apply(int),
        type="cloud",
        network_zone="us-west",
        ip_range="10.0.1.0/24",
    )

    # Firewall rules
    firewall = hcloud.Firewall(
        f"consult-{env}-firewall",
        name=f"consult-{env}",
        rules=[
            # SSH access (restrict in production)
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="22",
                source_ips=["0.0.0.0/0", "::/0"],
                description="SSH",
            ),
            # HTTP (redirects to HTTPS via Cloudflare)
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="80",
                source_ips=["0.0.0.0/0", "::/0"],
                description="HTTP",
            ),
            # HTTPS
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="443",
                source_ips=["0.0.0.0/0", "::/0"],
                description="HTTPS",
            ),
            # Django dev server (only in dev)
            *(
                [
                    hcloud.FirewallRuleArgs(
                        direction="in",
                        protocol="tcp",
                        port="8000",
                        source_ips=["0.0.0.0/0", "::/0"],
                        description="Django dev server",
                    )
                ]
                if env == "dev"
                else []
            ),
        ],
    )

    return NetworkResources(network=network, subnet=subnet, firewall=firewall)
