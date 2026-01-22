"""Hetzner persistent storage volumes."""

import pulumi_hcloud as hcloud

# Volume configuration by environment
VOLUME_CONFIG = {
    "dev": {
        "size": 20,  # 20GB, ~€1/mo
        "location": "hil",
    },
    "prod": {
        "size": 50,  # 50GB for production
        "location": "hil",
    },
}


def create_volume(env: str) -> hcloud.Volume:
    """Create persistent storage volume for application data.

    This volume stores:
    - Docker volumes (postgres data if local, media files, etc.)
    - Application logs
    - Backups

    Args:
        env: Environment name (dev, prod)

    Returns:
        The created Hetzner volume
    """
    volume_config = VOLUME_CONFIG.get(env, VOLUME_CONFIG["dev"])

    volume = hcloud.Volume(
        f"consult-{env}-storage",
        name=f"consult-{env}-storage",
        size=volume_config["size"],
        location=volume_config["location"],
        format="ext4",
        labels={
            "environment": env,
            "purpose": "app-storage",
            "managed_by": "pulumi",
        },
    )

    return volume
