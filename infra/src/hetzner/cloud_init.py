"""Cloud-init configuration for Django server bootstrap."""

from typing import Optional


def generate_cloud_init(env: str, deploy_ssh_public_key: Optional[str] = None) -> str:
    """Generate cloud-init script for Django server.

    Sets up:
    - Docker and Docker Compose
    - App directory structure
    - Volume mount point
    - Log rotation for Docker
    - Deploy SSH key for CI/automation access

    Args:
        env: Environment name (dev, prod)
        deploy_ssh_public_key: Optional SSH public key for CI/automation access

    Returns:
        Cloud-init YAML configuration string
    """
    # Add deploy key to authorized_keys if provided (for agent/CI access)
    ssh_keys_section = ""
    if deploy_ssh_public_key:
        ssh_keys_section = f"""
ssh_authorized_keys:
  - {deploy_ssh_public_key}
"""

    return f"""#cloud-config
package_update: true
package_upgrade: true
{ssh_keys_section}

packages:
  - ca-certificates
  - curl
  - git
  - htop
  - vim

runcmd:
  # Install Docker from official repository (includes compose plugin)
  - install -m 0755 -d /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  - chmod a+r /etc/apt/keyrings/docker.asc
  - |
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  - apt-get update
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

  # Enable and start Docker
  - systemctl enable docker
  - systemctl start docker

  # Create app directory
  - mkdir -p /app

  # Create data directory for volume mount
  - mkdir -p /data

  # Create log directory
  - mkdir -p /var/log/consult

  # Set up Docker log rotation
  - |
    cat > /etc/docker/daemon.json << 'DOCKER_EOF'
    {{
      "log-driver": "json-file",
      "log-opts": {{
        "max-size": "10m",
        "max-file": "3"
      }}
    }}
    DOCKER_EOF
  - systemctl restart docker

  # Create deploy script
  - |
    cat > /app/deploy.sh << 'DEPLOY_EOF'
    #!/bin/bash
    set -euo pipefail

    echo "=== Deployment started at $(date) ==="

    cd /app

    # Pull latest code
    if [ -d ".git" ]; then
      git pull origin main
    fi

    # Pull and restart containers
    docker compose pull
    docker compose up -d

    # Cleanup
    docker system prune -f

    echo "=== Deployment completed at $(date) ==="
    DEPLOY_EOF
  - chmod +x /app/deploy.sh

write_files:
  # Health check script
  - path: /app/health-check.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      curl -sf http://localhost:8000/health/ || exit 1

  # Systemd service for Django (optional, for non-compose deploys)
  - path: /etc/systemd/system/consult.service
    permissions: '0644'
    content: |
      [Unit]
      Description=Consult Django Application
      After=docker.service
      Requires=docker.service

      [Service]
      Type=simple
      User=root
      WorkingDirectory=/app
      ExecStart=/usr/bin/docker compose up
      ExecStop=/usr/bin/docker compose down
      Restart=always
      RestartSec=10

      [Install]
      WantedBy=multi-user.target

final_message: "Consult {env} server ready - $(date)"
"""
