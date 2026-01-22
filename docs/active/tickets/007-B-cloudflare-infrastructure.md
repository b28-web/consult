# 007-B: Cloudflare Infrastructure

**EP:** [EP-007-pulumi-infrastructure](../enhancement_proposals/EP-007-pulumi-infrastructure.md)
**Status:** pending

## Summary

Define all Cloudflare resources in Pulumi: DNS records, Workers, Pages projects, and security rules. These are the "always-working" edge systems.

## Acceptance Criteria

- [ ] DNS records for all domains managed in Pulumi
- [ ] Workers deployed via Pulumi (intake worker)
- [ ] Pages projects created for client sites
- [ ] Cloudflare proxy enabled for Django backend
- [ ] Basic WAF rules configured
- [ ] All resources tagged with environment

## Implementation Notes

### Directory Structure

```
infra/src/cloudflare/
├── __init__.py      # Exports all resources
├── dns.py           # DNS records
├── pages.py         # Pages projects
├── workers.py       # Workers scripts
└── security.py      # WAF, rate limiting
```

### DNS Records

`infra/src/cloudflare/dns.py`:
```python
import pulumi
import pulumi_cloudflare as cloudflare

def create_dns_records(zone_id: str, env: str) -> dict:
    """Create DNS records for the environment."""

    records = {}

    # Django backend (proxied through Cloudflare)
    records["api"] = cloudflare.Record(
        f"api-{env}",
        zone_id=zone_id,
        name="api" if env == "prod" else f"api-{env}",
        type="A",
        value=pulumi.Output.from_input("DJANGO_SERVER_IP"),  # From Hetzner
        proxied=True,
        ttl=1,  # Auto when proxied
    )

    # Intake worker
    records["intake"] = cloudflare.Record(
        f"intake-{env}",
        zone_id=zone_id,
        name="intake" if env == "prod" else f"intake-{env}",
        type="CNAME",
        value="consult-intake.workers.dev",
        proxied=True,
        ttl=1,
    )

    return records
```

### Workers

`infra/src/cloudflare/workers.py`:
```python
import pulumi
import pulumi_cloudflare as cloudflare
from pathlib import Path

def create_intake_worker(account_id: str, env: str) -> cloudflare.WorkerScript:
    """Deploy the intake worker."""

    # Read worker bundle (built by wrangler)
    worker_content = Path("../workers/intake/dist/index.js").read_text()

    return cloudflare.WorkerScript(
        f"intake-worker-{env}",
        account_id=account_id,
        name=f"consult-intake-{env}",
        content=worker_content,
        module=True,

        # Secrets injected from Doppler via Pulumi config
        secret_text_bindings=[
            cloudflare.WorkerScriptSecretTextBindingArgs(
                name="NEON_DATABASE_URL",
                text=pulumi.Config().require_secret("neon_database_url"),
            ),
            cloudflare.WorkerScriptSecretTextBindingArgs(
                name="INTAKE_API_KEY",
                text=pulumi.Config().require_secret("intake_api_key"),
            ),
        ],
    )


def create_worker_route(zone_id: str, worker_name: str, pattern: str) -> cloudflare.WorkerRoute:
    """Create a route for the worker."""

    return cloudflare.WorkerRoute(
        f"route-{worker_name}",
        zone_id=zone_id,
        pattern=pattern,
        script_name=worker_name,
    )
```

### Pages Projects

`infra/src/cloudflare/pages.py`:
```python
import pulumi
import pulumi_cloudflare as cloudflare

def create_pages_project(account_id: str, site_name: str, env: str) -> cloudflare.PagesProject:
    """Create a Pages project for a client site."""

    return cloudflare.PagesProject(
        f"pages-{site_name}-{env}",
        account_id=account_id,
        name=f"consult-{site_name}-{env}",
        production_branch="main",

        build_config=cloudflare.PagesProjectBuildConfigArgs(
            build_command="pnpm build",
            destination_dir="dist",
            root_dir=f"sites/{site_name}",
        ),

        deployment_configs=cloudflare.PagesProjectDeploymentConfigsArgs(
            production=cloudflare.PagesProjectDeploymentConfigsProductionArgs(
                environment_variables={
                    "NODE_VERSION": "20",
                },
            ),
        ),
    )


def create_pages_domain(
    account_id: str,
    project_name: str,
    domain: str,
) -> cloudflare.PagesDomain:
    """Attach a custom domain to a Pages project."""

    return cloudflare.PagesDomain(
        f"pages-domain-{domain.replace('.', '-')}",
        account_id=account_id,
        project_name=project_name,
        domain=domain,
    )
```

### Security Rules

`infra/src/cloudflare/security.py`:
```python
import pulumi_cloudflare as cloudflare

def create_waf_rules(zone_id: str) -> list:
    """Create basic WAF rules."""

    rules = []

    # Rate limiting for intake endpoint
    rules.append(cloudflare.RateLimit(
        "rate-limit-intake",
        zone_id=zone_id,
        threshold=100,
        period=60,
        match=cloudflare.RateLimitMatchArgs(
            request=cloudflare.RateLimitMatchRequestArgs(
                url_pattern="*intake.consult.io/*",
                schemes=["HTTP", "HTTPS"],
                methods=["POST"],
            ),
        ),
        action=cloudflare.RateLimitActionArgs(
            mode="simulate",  # Change to "ban" in prod
            timeout=60,
        ),
    ))

    return rules
```

### Environment-Specific Config

| Resource | Dev | Prod |
|----------|-----|------|
| DNS prefix | `api-dev`, `intake-dev` | `api`, `intake` |
| Worker name | `consult-intake-dev` | `consult-intake` |
| Pages project | `consult-coffee-shop-dev` | `consult-coffee-shop` |
| Rate limit mode | `simulate` | `ban` |

## Progress

(Updated as work proceeds)
