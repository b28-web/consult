# Consult

Multi-tenant web agency platform. Unified inbox, static sites, and CRM integration.

## Quick Start

### Prerequisites

- [Flox](https://flox.dev) - Development environment manager
- [Doppler](https://doppler.com) account - Secrets management

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd consult

# 2. Activate the development environment
flox activate

# 3. Configure Doppler (one time)
doppler login
doppler setup

# 4. Install dependencies and set up hooks
just setup

# 5. Run the development server
just dev
```

## Development Commands

Run `just` to see all available commands. Common ones:

```bash
just dev          # Start Django dev server
just test         # Run tests
just check        # Run all quality checks (lint, types, tests)
just format       # Auto-format code
just migrate      # Run database migrations
just shell        # Django shell
```

## Project Structure

```
consult/
├── apps/
│   └── web/              # Django application
├── sites/                # Astro static sites
├── workers/              # Cloudflare Workers
├── packages/             # Shared code
├── scripts/              # Utility scripts
├── .github/workflows/    # CI/CD
├── ARCHITECTURE.md       # System design docs
├── CLAUDE.md             # AI assistant context
└── justfile              # Development commands
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design and component overview
- [CLAUDE.md](./CLAUDE.md) - Conventions and AI assistant guidelines

## Environment

This project uses:
- **Flox** for deterministic dev environments
- **Doppler** for secrets (no .env files)
- **uv** for Python package management
- **ruff** for linting and formatting
- **mypy** for type checking
- **pytest** for testing

## CI/CD

- **CI** runs on every PR: lint, typecheck, test
- **Deploy to staging** on push to main
- **Deploy to production** via manual trigger

## License

Proprietary - All rights reserved.
