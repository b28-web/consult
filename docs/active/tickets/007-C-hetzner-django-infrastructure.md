# 007-C: Hetzner Django Infrastructure

**EP:** [EP-007-pulumi-infrastructure](../enhancement_proposals/EP-007-pulumi-infrastructure.md)
**Status:** completed

## Summary

Provision Django backend infrastructure on Hetzner Cloud US West (Hillsboro). Set up VPC, firewall, server, and persistent volume with Docker-based deployment.

## Acceptance Criteria

- [x] VPC network created in Hetzner US West
- [x] Firewall rules: SSH (restricted), HTTP/HTTPS (Cloudflare only)
- [x] CX22 server provisioned with Ubuntu 24.04
- [x] Volume attached for persistent data
- [x] Docker + Docker Compose installed via cloud-init
- [x] Server IP exported for Cloudflare DNS
- [x] SSH key managed in Pulumi

## Implementation Notes

### Directory Structure

```
infra/src/hetzner/
├── __init__.py      # Exports all resources
├── network.py       # VPC, subnets
├── firewall.py      # Security rules
├── server.py        # VM instance
├── volume.py        # Persistent storage
└── cloud_init.py    # Bootstrap script
```

### Network

`infra/src/hetzner/network.py`:
```python
import pulumi_hcloud as hcloud

def create_network(env: str) -> hcloud.Network:
    """Create VPC network."""

    return hcloud.Network(
        f"network-{env}",
        name=f"consult-{env}",
        ip_range="10.0.0.0/16",
    )


def create_subnet(network_id: str, env: str) -> hcloud.NetworkSubnet:
    """Create subnet in US West (Hillsboro)."""

    return hcloud.NetworkSubnet(
        f"subnet-{env}",
        network_id=network_id,
        type="cloud",
        network_zone="us-west",
        ip_range="10.0.1.0/24",
    )
```

### Firewall

`infra/src/hetzner/firewall.py`:
```python
import pulumi_hcloud as hcloud

# Cloudflare IP ranges (for HTTPS)
CLOUDFLARE_IPS = [
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

def create_firewall(env: str, admin_ips: list[str]) -> hcloud.Firewall:
    """Create firewall with strict rules."""

    return hcloud.Firewall(
        f"firewall-{env}",
        name=f"consult-{env}",
        rules=[
            # SSH from admin IPs only
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="22",
                source_ips=admin_ips,
                description="SSH from admin",
            ),
            # HTTP from Cloudflare only
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="80",
                source_ips=CLOUDFLARE_IPS,
                description="HTTP from Cloudflare",
            ),
            # HTTPS from Cloudflare only
            hcloud.FirewallRuleArgs(
                direction="in",
                protocol="tcp",
                port="443",
                source_ips=CLOUDFLARE_IPS,
                description="HTTPS from Cloudflare",
            ),
            # Allow all outbound
            hcloud.FirewallRuleArgs(
                direction="out",
                protocol="tcp",
                port="any",
                destination_ips=["0.0.0.0/0", "::/0"],
                description="Outbound TCP",
            ),
            hcloud.FirewallRuleArgs(
                direction="out",
                protocol="udp",
                port="any",
                destination_ips=["0.0.0.0/0", "::/0"],
                description="Outbound UDP",
            ),
        ],
    )
```

### Server

`infra/src/hetzner/server.py`:
```python
import pulumi
import pulumi_hcloud as hcloud

def create_server(
    env: str,
    network_id: str,
    firewall_id: str,
    ssh_key_id: str,
    cloud_init: str,
) -> hcloud.Server:
    """Create Django server."""

    return hcloud.Server(
        f"django-{env}",
        name=f"consult-django-{env}",
        server_type="cx22",  # 2 vCPU, 4GB RAM, €4.50/mo
        image="ubuntu-24.04",
        location="hil",  # Hillsboro, US West
        ssh_keys=[ssh_key_id],
        firewalls=[firewall_id],
        user_data=cloud_init,
        networks=[
            hcloud.ServerNetworkArgs(
                network_id=network_id,
                ip="10.0.1.10",
            ),
        ],
        labels={
            "env": env,
            "app": "django",
            "managed-by": "pulumi",
        },
    )


def create_ssh_key(env: str, public_key: str) -> hcloud.SshKey:
    """Create SSH key for server access."""

    return hcloud.SshKey(
        f"ssh-key-{env}",
        name=f"consult-{env}",
        public_key=public_key,
    )
```

### Volume

`infra/src/hetzner/volume.py`:
```python
import pulumi_hcloud as hcloud

def create_volume(env: str, server_id: str) -> hcloud.Volume:
    """Create persistent volume for Django data."""

    volume = hcloud.Volume(
        f"volume-{env}",
        name=f"consult-data-{env}",
        size=20,  # GB
        location="hil",
        format="ext4",
        labels={
            "env": env,
            "managed-by": "pulumi",
        },
    )

    # Attach to server
    hcloud.VolumeAttachment(
        f"volume-attachment-{env}",
        volume_id=volume.id,
        server_id=server_id,
        automount=True,
    )

    return volume
```

### Cloud-Init Bootstrap

`infra/src/hetzner/cloud_init.py`:
```python
def generate_cloud_init(env: str, doppler_token: str) -> str:
    """Generate cloud-init script for Django server."""

    return f"""#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-v2
  - curl
  - git

# Install Doppler CLI
runcmd:
  # Add Docker group
  - usermod -aG docker ubuntu

  # Install Doppler
  - curl -sLf https://cli.doppler.com/install.sh | sh

  # Create app directory
  - mkdir -p /opt/consult
  - chown ubuntu:ubuntu /opt/consult

  # Mount volume
  - mkdir -p /mnt/data
  - echo '/dev/sdb /mnt/data ext4 defaults 0 2' >> /etc/fstab
  - mount -a

  # Create systemd service for Django
  - |
    cat > /etc/systemd/system/consult-django.service << 'EOF'
    [Unit]
    Description=Consult Django
    After=docker.service
    Requires=docker.service

    [Service]
    Type=simple
    User=ubuntu
    WorkingDirectory=/opt/consult
    Environment="DOPPLER_TOKEN={doppler_token}"
    ExecStart=/usr/bin/doppler run -- docker compose up
    ExecStop=/usr/bin/docker compose down
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    EOF

  - systemctl daemon-reload
  - systemctl enable consult-django

# Write deployment script
write_files:
  - path: /opt/consult/deploy.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      set -euo pipefail
      cd /opt/consult
      git pull origin main
      doppler run -- docker compose pull
      doppler run -- docker compose up -d
      docker system prune -f

final_message: "Consult Django server ready"
"""
```

### Server Sizes Reference

| Type | vCPU | RAM | Storage | Monthly |
|------|------|-----|---------|---------|
| CX22 | 2 | 4 GB | 40 GB | €4.50 |
| CX32 | 4 | 8 GB | 80 GB | €8.98 |
| CX42 | 8 | 16 GB | 160 GB | €17.98 |

Start with CX22, scale up if needed.

## Progress

### 2026-01-22
- Created `firewall.py` with Cloudflare IP restrictions (IPv4 + IPv6)
  - SSH: restricted to admin IPs (configurable, open in dev only)
  - HTTP/HTTPS: only from Cloudflare proxy IPs
  - Django dev port 8000: only in dev environment
- Created `cloud_init.py` with server bootstrap script
  - Docker and Docker Compose installation
  - App directory structure (/app, /data, /var/log/consult)
  - Docker log rotation configuration
  - Deploy script for pulling and restarting containers
- Refactored `network.py` to focus on VPC and subnet only
- Updated `server.py` with:
  - SSH key resource creation (reads from Pulumi config)
  - Firewall attachment
  - Cloud-init integration
  - Proper dependency ordering with subnet
- Updated `__main__.py` to orchestrate all Hetzner resources
- All acceptance criteria met
