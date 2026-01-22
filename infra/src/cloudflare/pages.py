"""Cloudflare Pages for static site hosting.

Reads site configuration from sites/registry.yaml and creates
Cloudflare Pages projects for each site marked as ready.
"""

from pathlib import Path
from typing import Any

import pulumi
import pulumi_cloudflare as cloudflare
import yaml


def load_site_registry() -> dict[str, Any]:
    """Load site registry from sites/registry.yaml.

    Returns:
        Dictionary of site configurations keyed by slug.
    """
    # Registry is at repo_root/sites/registry.yaml
    # Pulumi runs from infra/, so go up one level
    registry_path = Path(__file__).parent.parent.parent.parent / "sites" / "registry.yaml"

    if not registry_path.exists():
        pulumi.log.warn(f"Site registry not found at {registry_path}, no sites will be created")
        return {}

    with open(registry_path) as f:
        data = yaml.safe_load(f)

    return data.get("sites", {}) if data else {}


def create_pages_projects(env: str) -> dict[str, Any]:
    """Create Cloudflare Pages projects for registered sites.

    Reads from sites/registry.yaml and creates Pages projects for each
    site where ready=true. Custom domains are attached for prod environment
    if specified in the registry.

    Args:
        env: Environment name (dev, prod)

    Returns:
        Dictionary of Pages project resources keyed by site slug
    """
    config = pulumi.Config()
    account_id = config.require("cloudflare_account_id")

    registry = load_site_registry()
    projects: dict[str, Any] = {}

    for slug, site_config in registry.items():
        # Skip sites not marked as ready
        if not site_config.get("ready", False):
            pulumi.log.info(f"Skipping site '{slug}' (not ready)")
            continue

        # Get environment-specific config
        env_config = site_config.get(env, site_config.get("dev", {}))
        custom_domain = env_config.get("domain") if env_config else None

        # Project name includes env for non-prod
        project_name = f"consult-{slug}" if env == "prod" else f"consult-{slug}-{env}"

        pulumi.log.info(f"Creating Pages project: {project_name}")

        project = cloudflare.PagesProject(
            f"consult-{env}-pages-{slug}",
            account_id=account_id,
            name=project_name,
            production_branch="main",
            build_config=cloudflare.PagesProjectBuildConfigArgs(
                build_command="pnpm build",
                destination_dir="dist",
                root_dir=f"sites/{slug}",
            ),
        )

        site_resources: dict[str, Any] = {"project": project}

        # Attach custom domain if specified
        if custom_domain:
            pulumi.log.info(f"  Attaching domain: {custom_domain}")
            domain = cloudflare.PagesDomain(
                f"consult-{env}-pages-domain-{slug}",
                account_id=account_id,
                project_name=project.name,
                domain=custom_domain,
            )
            site_resources["domain"] = domain

        projects[slug] = site_resources

    if not projects:
        pulumi.log.warn("No sites marked as ready in registry")

    return projects
