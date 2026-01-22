"""Hetzner server provisioning for Django backend."""

from typing import Optional

import pulumi
import pulumi_hcloud as hcloud

from src.hetzner.cloud_init import generate_cloud_init

# Server configuration by environment
SERVER_CONFIG = {
    "dev": {
        "server_type": "cpx11",  # 2 vCPU, 2GB RAM (cx22 deprecated)
        "location": "hil",  # Hillsboro (US West)
    },
    "prod": {
        "server_type": "cpx21",  # 3 vCPU, 4GB RAM
        "location": "hil",
    },
}


def create_ssh_key(env: str) -> hcloud.SshKey:
    """Create SSH key for server access.

    The public key is read from Pulumi config (set via `just setup-infra`).

    Args:
        env: Environment name (dev, prod)

    Returns:
        The created Hetzner SSH key
    """
    config = pulumi.Config()
    public_key = config.require_secret("ssh_public_key")

    return hcloud.SshKey(
        f"consult-{env}-ssh-key",
        name=f"consult-{env}",
        public_key=public_key,
        labels={
            "environment": env,
            "managed_by": "pulumi",
        },
    )


def create_server(
    env: str,
    network_id: pulumi.Output[int],
    subnet: hcloud.NetworkSubnet,
    firewall_id: pulumi.Output[int],
    ssh_key_id: pulumi.Output[int],
    volume_id: pulumi.Output[int],
    deploy_ssh_public_key: Optional[str] = None,
) -> hcloud.Server:
    """Create Django application server.

    Args:
        env: Environment name (dev, prod)
        network_id: ID of the VPC network
        subnet: The network subnet (for dependency ordering)
        firewall_id: ID of the firewall to attach
        ssh_key_id: ID of the SSH key for access
        volume_id: ID of the storage volume to attach
        deploy_ssh_public_key: Optional SSH public key for CI/automation access

    Returns:
        The created Hetzner server
    """
    server_config = SERVER_CONFIG.get(env, SERVER_CONFIG["dev"])
    cloud_init = generate_cloud_init(env, deploy_ssh_public_key)

    server = hcloud.Server(
        f"consult-{env}-django",
        name=f"consult-{env}-django",
        server_type=server_config["server_type"],
        location=server_config["location"],
        image="ubuntu-24.04",
        ssh_keys=[ssh_key_id],
        firewall_ids=[firewall_id],
        user_data=cloud_init,
        public_nets=[
            hcloud.ServerPublicNetArgs(
                ipv4_enabled=True,
                ipv6_enabled=True,
            )
        ],
        labels={
            "environment": env,
            "service": "django",
            "managed_by": "pulumi",
        },
        opts=pulumi.ResourceOptions(depends_on=[subnet]),
    )

    # Attach to private network
    hcloud.ServerNetwork(
        f"consult-{env}-django-network",
        server_id=server.id.apply(int),
        network_id=network_id,
    )

    # Attach storage volume
    hcloud.VolumeAttachment(
        f"consult-{env}-volume-attachment",
        server_id=server.id.apply(int),
        volume_id=volume_id,
        automount=True,
    )

    return server
