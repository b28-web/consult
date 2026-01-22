"""Hetzner server provisioning for Django backend."""

import pulumi
import pulumi_hcloud as hcloud

# Server configuration by environment
SERVER_CONFIG = {
    "dev": {
        "server_type": "cx22",  # 2 vCPU, 4GB RAM, €4.50/mo
        "location": "hil",  # Hillsboro (US West)
    },
    "prod": {
        "server_type": "cx22",  # Start small, scale as needed
        "location": "hil",
    },
}


def create_server(
    env: str,
    network_id: pulumi.Output[int],
    volume_id: pulumi.Output[int],
) -> hcloud.Server:
    """Create Django application server.

    Args:
        env: Environment name (dev, prod)
        network_id: ID of the VPC network
        volume_id: ID of the storage volume to attach

    Returns:
        The created Hetzner server
    """
    config = pulumi.Config()
    ssh_key_name = config.get("ssh_key_name") or f"consult-{env}"

    server_config = SERVER_CONFIG.get(env, SERVER_CONFIG["dev"])

    # Cloud-init script to set up Docker
    cloud_init = """#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-plugin
  - curl
  - git

runcmd:
  # Enable Docker
  - systemctl enable docker
  - systemctl start docker

  # Create app directory
  - mkdir -p /app
  - chown -R 1000:1000 /app

  # Mount the volume (will be formatted on first use)
  - mkdir -p /data
  - echo "Volume will be mounted by Hetzner"

write_files:
  - path: /etc/docker/daemon.json
    content: |
      {
        "log-driver": "json-file",
        "log-opts": {
          "max-size": "10m",
          "max-file": "3"
        }
      }
"""

    server = hcloud.Server(
        f"consult-{env}-django",
        name=f"consult-{env}-django",
        server_type=server_config["server_type"],
        location=server_config["location"],
        image="ubuntu-24.04",
        ssh_keys=[ssh_key_name],
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
    )

    # Attach to private network
    hcloud.ServerNetwork(
        f"consult-{env}-django-network",
        server_id=server.id.apply(int),
        network_id=network_id.apply(int),
    )

    # Attach storage volume
    hcloud.VolumeAttachment(
        f"consult-{env}-volume-attachment",
        server_id=server.id.apply(int),
        volume_id=volume_id.apply(int),
        automount=True,
    )

    return server
