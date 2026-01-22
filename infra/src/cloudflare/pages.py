"""Cloudflare Pages for static site hosting."""

from typing import Any

import pulumi
import pulumi_cloudflare as cloudflare

# Client sites to deploy
# Each site gets its own Pages project
CLIENT_SITES = [
    "coffee-shop",
    # Future sites will be added here as they're created
    # "hauler",
    # "cleaning",
    # "landscaper",
    # "barber",
]


def create_pages_projects(env: str) -> dict[str, Any]:
    """Create Cloudflare Pages projects for client sites.

    Note: Actual deployments happen via `wrangler pages deploy` in CI/CD.
    This just creates the Pages project infrastructure.

    Args:
        env: Environment name (dev, prod)

    Returns:
        Dictionary of Pages project resources
    """
    config = pulumi.Config()
    account_id = config.require("cloudflare_account_id")

    projects: dict[str, Any] = {}

    for site in CLIENT_SITES:
        # Project name includes env for non-prod
        project_name = f"consult-{site}" if env == "prod" else f"consult-{site}-{env}"

        project = cloudflare.PagesProject(
            f"consult-{env}-pages-{site}",
            account_id=account_id,
            name=project_name,
            production_branch="main",
            build_config=cloudflare.PagesProjectBuildConfigArgs(
                build_command="pnpm build",
                destination_dir="dist",
                root_dir=f"sites/{site}",
            ),
        )
        projects[site] = project

    return projects
