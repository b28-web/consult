"""Cloud-init configuration for Django server bootstrap."""


def generate_cloud_init(env: str) -> str:
    """Generate cloud-init script for Django server.

    Sets up:
    - Docker and Docker Compose
    - App directory structure
    - Volume mount point
    - Log rotation for Docker

    Args:
        env: Environment name (dev, prod)

    Returns:
        Cloud-init YAML configuration string
    """
    return f"""#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-plugin
  - curl
  - git
  - htop
  - vim

runcmd:
  # Enable and start Docker
  - systemctl enable docker
  - systemctl start docker

  # Add ubuntu user to docker group
  - usermod -aG docker ubuntu

  # Create app directory
  - mkdir -p /app
  - chown -R ubuntu:ubuntu /app

  # Create data directory for volume mount
  - mkdir -p /data
  - chown -R ubuntu:ubuntu /data

  # Create log directory
  - mkdir -p /var/log/consult
  - chown -R ubuntu:ubuntu /var/log/consult

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
  - chown ubuntu:ubuntu /app/deploy.sh

write_files:
  # Health check script
  - path: /app/health-check.sh
    permissions: '0755'
    owner: ubuntu:ubuntu
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
      User=ubuntu
      WorkingDirectory=/app
      ExecStart=/usr/bin/docker compose up
      ExecStop=/usr/bin/docker compose down
      Restart=always
      RestartSec=10

      [Install]
      WantedBy=multi-user.target

final_message: "Consult {env} server ready - $(date)"
"""
