"""Consult Infrastructure - Pulumi Entry Point.

This module orchestrates infrastructure provisioning across:
- Cloudflare: DNS, Pages (static sites), Workers (edge functions)
- Hetzner: Django backend servers, volumes, networking
"""

import pulumi
from src import outputs
from src.cloudflare import dns, pages, security, workers
from src.hetzner import firewall, network, server, volume

# Get environment from stack config
config = pulumi.Config()
env = config.require("environment")

# =============================================================================
# Hetzner Infrastructure
# =============================================================================

# VPC network and subnet
vpc = network.create_network(env)

# Firewall (SSH restricted, HTTP/HTTPS from Cloudflare only)
hetzner_firewall = firewall.create_firewall(env)

# SSH key for server access
ssh_key = server.create_ssh_key(env)

# Persistent storage volume
storage_volume = volume.create_volume(env)

# Django server
django_server = server.create_server(
    env=env,
    network_id=vpc.network.id.apply(int),
    subnet=vpc.subnet,
    firewall_id=hetzner_firewall.id.apply(int),
    ssh_key_id=ssh_key.id.apply(int),
    volume_id=storage_volume.id.apply(int),
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

# Cloudflare security rules (WAF, rate limiting)
security_rules = security.create_security_rules(env)

# =============================================================================
# Outputs
# =============================================================================

outputs.export_outputs(
    env=env,
    django_server=django_server,
    dns_records=dns_records,
    sites=sites,
    intake_worker=intake_worker,
    security_rules=security_rules,
)
