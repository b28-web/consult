"""Hetzner network infrastructure: VPC and subnets."""

from dataclasses import dataclass

import pulumi_hcloud as hcloud


@dataclass
class NetworkResources:
    """Container for network-related resources."""

    network: hcloud.Network
    subnet: hcloud.NetworkSubnet


def create_network(env: str) -> NetworkResources:
    """Create VPC network with subnet in US West.

    Args:
        env: Environment name (dev, prod)

    Returns:
        NetworkResources containing network and subnet
    """
    # Private network for internal communication
    network = hcloud.Network(
        f"consult-{env}-network",
        name=f"consult-{env}",
        ip_range="10.0.0.0/16",
        labels={
            "environment": env,
            "managed_by": "pulumi",
        },
    )

    # Subnet in the US West region (Hillsboro)
    subnet = hcloud.NetworkSubnet(
        f"consult-{env}-subnet",
        network_id=network.id.apply(int),
        type="cloud",
        network_zone="us-west",
        ip_range="10.0.1.0/24",
    )

    return NetworkResources(network=network, subnet=subnet)
