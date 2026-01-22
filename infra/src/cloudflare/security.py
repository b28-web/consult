"""Cloudflare security rules: WAF, rate limiting, and firewall."""

from typing import Any

import pulumi
import pulumi_cloudflare as cloudflare


def create_security_rules(env: str) -> dict[str, Any]:
    """Create Cloudflare security rules.

    Args:
        env: Environment name (dev, prod)

    Returns:
        Dictionary of security rule resources
    """
    config = pulumi.Config()
    zone_id = config.require("cloudflare_zone_id")
    domain = config.require("domain")

    rules: dict[str, Any] = {}

    # Subdomain prefix for non-prod
    prefix = "" if env == "prod" else f"{env}."

    # Rate limiting for intake endpoint (form submissions)
    # Prevents spam/abuse of the intake worker
    intake_rate_limit = cloudflare.RateLimit(
        f"consult-{env}-intake-rate-limit",
        zone_id=zone_id,
        threshold=100,  # requests per period
        period=60,  # seconds
        match=cloudflare.RateLimitMatchArgs(
            request=cloudflare.RateLimitMatchRequestArgs(
                url_pattern=f"*{prefix}intake.{domain}/*",
                schemes=["HTTP", "HTTPS"],
                methods=["POST"],
            ),
        ),
        action=cloudflare.RateLimitActionArgs(
            mode="simulate" if env == "dev" else "ban",
            timeout=60,
        ),
        disabled=False,
        description=f"Rate limit intake submissions ({env})",
    )
    rules["intake_rate_limit"] = intake_rate_limit

    # Rate limiting for API endpoints
    # Protects Django backend from abuse
    api_rate_limit = cloudflare.RateLimit(
        f"consult-{env}-api-rate-limit",
        zone_id=zone_id,
        threshold=300,  # higher limit for API
        period=60,
        match=cloudflare.RateLimitMatchArgs(
            request=cloudflare.RateLimitMatchRequestArgs(
                url_pattern=f"*{prefix}api.{domain}/*",
                schemes=["HTTP", "HTTPS"],
                methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            ),
        ),
        action=cloudflare.RateLimitActionArgs(
            mode="simulate" if env == "dev" else "ban",
            timeout=60,
        ),
        disabled=False,
        description=f"Rate limit API requests ({env})",
    )
    rules["api_rate_limit"] = api_rate_limit

    # Firewall rule: Block requests without proper headers to API
    # Requires requests to have a valid User-Agent (blocks basic bots)
    api_ua_filter = cloudflare.Filter(
        f"consult-{env}-api-ua-filter",
        zone_id=zone_id,
        expression=(
            f'(http.host eq "{prefix}api.{domain}" and len(http.user_agent) eq 0)'
        ),
        description=f"Block empty User-Agent on API ({env})",
    )

    api_ua_rule = cloudflare.FirewallRule(
        f"consult-{env}-api-ua-block",
        zone_id=zone_id,
        filter_id=api_ua_filter.id,
        action="block",
        description=f"Block empty User-Agent on API ({env})",
        priority=1,
    )
    rules["api_ua_filter"] = api_ua_filter
    rules["api_ua_rule"] = api_ua_rule

    # Firewall rule: Challenge suspicious traffic to dashboard
    # Admin/dashboard gets extra protection
    dashboard_challenge_filter = cloudflare.Filter(
        f"consult-{env}-dashboard-challenge-filter",
        zone_id=zone_id,
        expression=(
            f'(http.host eq "{prefix}dashboard.{domain}" and cf.threat_score gt 10)'
        ),
        description=f"Challenge suspicious dashboard traffic ({env})",
    )

    dashboard_challenge_rule = cloudflare.FirewallRule(
        f"consult-{env}-dashboard-challenge",
        zone_id=zone_id,
        filter_id=dashboard_challenge_filter.id,
        action="challenge",
        description=f"Challenge suspicious dashboard traffic ({env})",
        priority=2,
    )
    rules["dashboard_challenge_filter"] = dashboard_challenge_filter
    rules["dashboard_challenge_rule"] = dashboard_challenge_rule

    return rules
