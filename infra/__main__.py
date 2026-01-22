"""Consult Infrastructure - Pulumi Entry Point.

This module orchestrates infrastructure provisioning across:
- Cloudflare: DNS, Pages (static sites), Workers (edge functions)
- Hetzner: Django backend servers, volumes, networking
"""

import pulumi

from src import outputs
from src.cloudflare import dns, pages, workers
from src.hetzner import network, server, volume

# Get environment from stack config
config = pulumi.Config()
env = config.require("environment")

# =============================================================================
# Hetzner Infrastructure
# =============================================================================

# Network (VPC, firewall rules)
vpc = network.create_network(env)

# Persistent storage volume
storage_volume = volume.create_volume(env)

# Django server
django_server = server.create_server(
    env=env,
    network_id=vpc.network.id,
    volume_id=storage_volume.id,
)

# =============================================================================
# Cloudflare Infrastructure
# =============================================================================

# DNS records (point to Hetzner servers)
dns_records = dns.create_dns_records(
    env=env,
    server_ip=django_server.ipv4_address,
)

# Cloudflare Pages (static sites)
sites = pages.create_pages_projects(env)

# Cloudflare Workers (edge functions)
intake_worker = workers.create_workers(env)

# =============================================================================
# Outputs
# =============================================================================

outputs.export_outputs(
    env=env,
    django_server=django_server,
    dns_records=dns_records,
    sites=sites,
    intake_worker=intake_worker,
)
