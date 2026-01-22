# Justfile for Consult development commands
# Run `just` to see available commands
# Documentation: https://just.systems/man/en/

# Default recipe - show help
default:
    @just --list

# =============================================================================
# Setup
# =============================================================================

# Install all dependencies
install:
    uv sync --dev

# Set up pre-commit hooks
setup-hooks:
    uv run pre-commit install

# Full setup for new developers
setup: install setup-hooks
    @echo "Setup complete! Run 'flox activate' to enter the dev environment."
    @echo "Then run 'just setup-infra' to configure Doppler and Neon."

# =============================================================================
# Infrastructure Setup (Doppler + Neon)
# =============================================================================

# Required secrets for each component
DJANGO_SECRETS := "SECRET_KEY DEBUG ALLOWED_HOSTS DATABASE_URL"
WORKER_SECRETS := "NEON_DATABASE_URL INTAKE_API_KEY"
DEPLOY_SECRETS := "CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID"

# Interactive infrastructure setup wizard
setup-infra:
    #!/usr/bin/env bash
    set -euo pipefail

    # Colors
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m'

    # Helper functions
    header() { echo -e "\n${BOLD}${BLUE}═══ $1 ═══${NC}\n"; }
    success() { echo -e "${GREEN}✓${NC} $1"; }
    warn() { echo -e "${YELLOW}!${NC} $1"; }
    error() { echo -e "${RED}✗${NC} $1"; }
    info() { echo -e "${DIM}  $1${NC}"; }

    prompt_enter() {
        echo ""
        read -p "Press Enter to continue..."
    }

    prompt_yes_no() {
        local prompt=$1
        local default=${2:-y}
        local yn
        if [ "$default" = "y" ]; then
            read -p "$prompt [Y/n]: " yn
            yn=${yn:-y}
        else
            read -p "$prompt [y/N]: " yn
            yn=${yn:-n}
        fi
        [[ "$yn" =~ ^[Yy] ]]
    }

    check_secret() {
        doppler secrets get "$1" --plain &>/dev/null 2>&1
    }

    get_secret() {
        doppler secrets get "$1" --plain 2>/dev/null || echo ""
    }

    set_secret() {
        local name=$1
        local value=$2
        echo -e "${DIM}Setting $name...${NC}"
        doppler secrets set "$name=$value" --silent
        success "$name configured"
    }

    # =========================================================================
    echo -e "${BOLD}"
    echo "  ╔═══════════════════════════════════════════╗"
    echo "  ║     Consult Infrastructure Wizard         ║"
    echo "  ╚═══════════════════════════════════════════╝"
    echo -e "${NC}"

    # =========================================================================
    header "Step 1: Doppler Access"
    # =========================================================================

    if ! command -v doppler &> /dev/null; then
        error "Doppler CLI not installed"
        echo ""
        echo "Install with:"
        echo "  brew install dopplerhq/cli/doppler"
        exit 1
    fi
    success "Doppler CLI installed"

    if ! doppler secrets --only-names &> /dev/null; then
        error "Cannot access Doppler"
        echo ""
        echo "You need a Doppler service token. Here's how:"
        echo ""
        echo "  1. Go to: ${BLUE}https://dashboard.doppler.com${NC}"
        echo "  2. Select project: ${BOLD}consult${NC}"
        echo "  3. Click: ${BOLD}Access → Service Tokens → Generate${NC}"
        echo "  4. Name it: ${BOLD}dev_cli${NC}, Config: ${BOLD}dev${NC}"
        echo "  5. Copy the token (starts with dp.st.)"
        echo ""
        echo "Then either:"
        echo "  export DOPPLER_TOKEN=\"dp.st.xxx\""
        echo ""
        echo "Or add to .secrets.local:"
        echo "  export DOPPLER_TOKEN=\"dp.st.xxx\""
        exit 1
    fi
    success "Doppler access configured"

    # =========================================================================
    header "Step 2: Current Status"
    # =========================================================================

    MISSING=()

    echo "Django secrets:"
    for secret in SECRET_KEY DEBUG ALLOWED_HOSTS DATABASE_URL; do
        if check_secret "$secret"; then
            success "$secret"
        else
            error "$secret"
            MISSING+=("$secret")
        fi
    done

    echo ""
    echo "Worker secrets:"
    for secret in NEON_DATABASE_URL INTAKE_API_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            error "$secret"
            MISSING+=("$secret")
        fi
    done

    echo ""
    echo "Infrastructure secrets (for deployment):"
    for secret in HETZNER_API_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_ZONE_ID SSH_PUBLIC_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            warn "$secret (not set)"
        fi
    done

    echo ""
    echo "Optional secrets (for specific features):"
    for secret in TWILIO_AUTH_TOKEN TWILIO_ACCOUNT_SID RESEND_API_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            warn "$secret (not set)"
        fi
    done

    if [ ${#MISSING[@]} -eq 0 ]; then
        header "All Done!"
        success "All required secrets are configured for local development"
        echo ""
        echo "Next steps:"
        echo "  ${BOLD}just dev${NC}             # Start Django dev server"
        echo "  ${BOLD}just test-local${NC}      # Run full integration tests"
        echo ""
        echo "For deployment, also configure infrastructure secrets:"
        echo "  ${BOLD}just setup-infra${NC}     # Run again to see status"
        exit 0
    fi

    echo ""
    echo -e "${YELLOW}Missing ${#MISSING[@]} required secret(s): ${MISSING[*]}${NC}"

    # =========================================================================
    header "Step 3: Configure Missing Secrets"
    # =========================================================================

    # --- AUTO-GENERATED SECRETS ---

    # SECRET_KEY
    if [[ " ${MISSING[*]} " =~ " SECRET_KEY " ]]; then
        echo -e "${BOLD}SECRET_KEY${NC} - Django cryptographic signing key"
        info "Used for sessions, CSRF, password reset tokens"
        info "Must be unique and secret in production"
        echo ""

        if prompt_yes_no "Generate and set SECRET_KEY automatically?"; then
            SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
            set_secret "SECRET_KEY" "$SECRET_KEY"
        else
            echo "Skipped. Set manually with: doppler secrets set SECRET_KEY=yourkey"
        fi
        echo ""
    fi

    # DEBUG
    if [[ " ${MISSING[*]} " =~ " DEBUG " ]]; then
        echo -e "${BOLD}DEBUG${NC} - Django debug mode"
        info "True = detailed error pages (dev only!)"
        info "False = production mode"
        echo ""

        if prompt_yes_no "Set DEBUG=True for development?"; then
            set_secret "DEBUG" "True"
        else
            set_secret "DEBUG" "False"
        fi
        echo ""
    fi

    # ALLOWED_HOSTS
    if [[ " ${MISSING[*]} " =~ " ALLOWED_HOSTS " ]]; then
        echo -e "${BOLD}ALLOWED_HOSTS${NC} - Valid hostnames for Django"
        info "Comma-separated list of allowed domains"
        info "Dev: localhost,127.0.0.1"
        info "Prod: yourdomain.com,www.yourdomain.com"
        echo ""

        if prompt_yes_no "Set ALLOWED_HOSTS for local development?"; then
            set_secret "ALLOWED_HOSTS" "localhost,127.0.0.1"
        else
            read -p "Enter ALLOWED_HOSTS (comma-separated): " ALLOWED_HOSTS
            set_secret "ALLOWED_HOSTS" "$ALLOWED_HOSTS"
        fi
        echo ""
    fi

    # INTAKE_API_KEY
    if [[ " ${MISSING[*]} " =~ " INTAKE_API_KEY " ]]; then
        echo -e "${BOLD}INTAKE_API_KEY${NC} - API key for intake worker"
        info "Validates requests to the intake endpoint"
        info "Shared between client sites and worker"
        echo ""

        if prompt_yes_no "Generate and set INTAKE_API_KEY automatically?"; then
            INTAKE_API_KEY=$(openssl rand -hex 32)
            set_secret "INTAKE_API_KEY" "$INTAKE_API_KEY"
        else
            echo "Skipped. Set manually with: doppler secrets set INTAKE_API_KEY=yourkey"
        fi
        echo ""
    fi

    # --- USER-PROVIDED SECRETS (Neon) ---

    NEED_NEON=false
    if [[ " ${MISSING[*]} " =~ " DATABASE_URL " ]] || [[ " ${MISSING[*]} " =~ " NEON_DATABASE_URL " ]]; then
        NEED_NEON=true
    fi

    if [ "$NEED_NEON" = true ]; then
        header "Step 4: Neon Database Setup"

        echo "You need a Neon Postgres database. Two connection strings are required:"
        echo ""
        echo "  ${BOLD}DATABASE_URL${NC} (pooled) - For Django"
        info "Has '-pooler' in the hostname"
        info "Example: postgres://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb"
        echo ""
        echo "  ${BOLD}NEON_DATABASE_URL${NC} (direct) - For Workers"
        info "No '-pooler' in the hostname"
        info "Example: postgres://user:pass@ep-xxx.region.aws.neon.tech/neondb"
        echo ""

        if ! check_secret "DATABASE_URL" || ! check_secret "NEON_DATABASE_URL"; then
            echo -e "${BOLD}To get these:${NC}"
            echo "  1. Go to: ${BLUE}https://console.neon.tech${NC}"
            echo "  2. Create or select project: ${BOLD}consult${NC}"
            echo "  3. Go to: ${BOLD}Dashboard → Connection string${NC}"
            echo "  4. Copy the ${BOLD}pooled${NC} string (toggle 'Pooled connection')"
            echo "  5. Copy the ${BOLD}direct${NC} string (toggle off 'Pooled connection')"
            echo ""
            echo -e "${DIM}Both should end with ?sslmode=require${NC}"
            prompt_enter
        fi

        # DATABASE_URL
        if [[ " ${MISSING[*]} " =~ " DATABASE_URL " ]]; then
            echo ""
            echo -e "${BOLD}Enter DATABASE_URL${NC} (pooled, with -pooler in hostname):"
            read -p "> " DATABASE_URL

            if [ -n "$DATABASE_URL" ]; then
                if [[ "$DATABASE_URL" != *"pooler"* ]]; then
                    warn "This doesn't look like a pooled URL (no 'pooler' in hostname)"
                    if ! prompt_yes_no "Use it anyway?"; then
                        echo "Skipped."
                        DATABASE_URL=""
                    fi
                fi
                if [ -n "$DATABASE_URL" ]; then
                    set_secret "DATABASE_URL" "$DATABASE_URL"
                fi
            else
                echo "Skipped. Set manually with: doppler secrets set DATABASE_URL=..."
            fi
        fi

        # NEON_DATABASE_URL
        if [[ " ${MISSING[*]} " =~ " NEON_DATABASE_URL " ]]; then
            echo ""
            echo -e "${BOLD}Enter NEON_DATABASE_URL${NC} (direct, without -pooler):"
            read -p "> " NEON_DATABASE_URL

            if [ -n "$NEON_DATABASE_URL" ]; then
                if [[ "$NEON_DATABASE_URL" == *"pooler"* ]]; then
                    warn "This looks like a pooled URL (has 'pooler' in hostname)"
                    if ! prompt_yes_no "Use it anyway?"; then
                        echo "Skipped."
                        NEON_DATABASE_URL=""
                    fi
                fi
                if [ -n "$NEON_DATABASE_URL" ]; then
                    set_secret "NEON_DATABASE_URL" "$NEON_DATABASE_URL"
                fi
            else
                echo "Skipped. Set manually with: doppler secrets set NEON_DATABASE_URL=..."
            fi
        fi
    fi

    # =========================================================================
    header "Final Status"
    # =========================================================================

    STILL_MISSING=()

    for secret in SECRET_KEY DEBUG ALLOWED_HOSTS DATABASE_URL NEON_DATABASE_URL INTAKE_API_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            error "$secret"
            STILL_MISSING+=("$secret")
        fi
    done

    echo ""
    if [ ${#STILL_MISSING[@]} -eq 0 ]; then
        echo -e "${GREEN}${BOLD}All required secrets configured!${NC}"
        echo ""
        echo "Next steps:"
        echo "  ${BOLD}just migrate${NC}        # Run database migrations"
        echo "  ${BOLD}just dev${NC}            # Start Django dev server"
        echo "  ${BOLD}just deploy-worker${NC}  # Deploy intake worker"
    else
        echo -e "${YELLOW}Still missing: ${STILL_MISSING[*]}${NC}"
        echo ""
        echo "Run ${BOLD}just setup-infra${NC} again after setting them."
        echo "Or set manually: doppler secrets set NAME=value"
    fi

# Quick check if all secrets are present (non-interactive)
check-secrets:
    #!/usr/bin/env bash
    set -euo pipefail
    MISSING=0

    for secret in SECRET_KEY DEBUG ALLOWED_HOSTS DATABASE_URL NEON_DATABASE_URL INTAKE_API_KEY; do
        if ! doppler secrets get "$secret" --plain &>/dev/null 2>&1; then
            echo "Missing: $secret"
            MISSING=$((MISSING + 1))
        fi
    done

    if [ $MISSING -eq 0 ]; then
        echo "All required secrets present"
        exit 0
    else
        echo ""
        echo "$MISSING secret(s) missing. Run 'just setup-infra' for guidance."
        exit 1
    fi

# Switch Doppler environment
doppler-env ENV:
    doppler setup --config {{ENV}}
    @echo "Switched to {{ENV}} environment"
    @doppler configure

# =============================================================================
# Development
# =============================================================================

# Run Django development server
dev:
    doppler run -- uv run python apps/web/manage.py runserver

# =============================================================================
# Local Testing (Docker Compose)
# =============================================================================

# Start all local services in containers
dev-start:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Starting local services via Docker Compose..."
    doppler run -- docker compose up -d --build
    echo ""
    echo "Services starting..."
    echo "  Django:  http://localhost:8000"
    echo "  Worker:  http://localhost:8787"
    echo ""
    echo "Run 'just dev-logs' to tail logs"
    echo "Run 'just smoke-test' to verify"
    echo "Run 'just dev-stop' to stop"

# Stop all local services
dev-stop:
    docker compose down

# Show status of local services
dev-status:
    docker compose ps

# Tail logs from all services
dev-logs:
    docker compose logs -f

# Tail logs from specific service
dev-log SERVICE:
    docker compose logs -f {{SERVICE}}

# Health check / smoke test for running services
smoke-test:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Running smoke tests..."
    echo ""
    FAILED=0

    # Test Django
    echo -n "Django /admin/login/... "
    if curl -sf http://localhost:8000/admin/login/ > /dev/null 2>&1; then
        echo "✓"
    else
        echo "✗ FAILED"
        FAILED=$((FAILED + 1))
    fi

    # Test Worker health
    echo -n "Worker /health... "
    if curl -sf http://localhost:8787/health > /dev/null 2>&1; then
        echo "✓"
    else
        echo "✗ FAILED"
        FAILED=$((FAILED + 1))
    fi

    echo ""
    if [ $FAILED -eq 0 ]; then
        echo "All smoke tests passed!"
    else
        echo "$FAILED test(s) failed"
        exit 1
    fi

# Test form submission end-to-end (requires services running)
test-intake:
    doppler run -- uv run python scripts/test_intake.py

# Run full local test suite (start services, test, stop)
test-local:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "╔═══════════════════════════════════════╗"
    echo "║     Local Integration Tests           ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""

    # Cleanup on exit
    cleanup() {
        echo ""
        echo "Cleaning up..."
        docker compose down
    }
    trap cleanup EXIT

    # Start services
    echo "Starting services via Docker Compose..."
    doppler run -- docker compose up -d --build

    # Wait for services to be healthy
    echo "Waiting for services to be healthy..."
    for i in {1..30}; do
        DJANGO_HEALTH=$(docker compose ps django --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        WORKER_HEALTH=$(docker compose ps worker --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

        if [ "$DJANGO_HEALTH" = "healthy" ] && [ "$WORKER_HEALTH" = "healthy" ]; then
            echo "All services healthy!"
            break
        fi

        if [ $i -eq 30 ]; then
            echo "Timeout waiting for services to be healthy"
            echo "Django: $DJANGO_HEALTH, Worker: $WORKER_HEALTH"
            docker compose logs
            exit 1
        fi

        echo "  Waiting... (django=$DJANGO_HEALTH, worker=$WORKER_HEALTH)"
        sleep 2
    done

    echo ""

    # Run smoke tests
    just smoke-test

    echo ""

    # Run intake test
    just test-intake

    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║     ALL TESTS PASSED                  ║"
    echo "╚═══════════════════════════════════════╝"

# Run Django shell
shell:
    doppler run -- uv run python apps/web/manage.py shell

# Run database migrations
migrate:
    doppler run -- uv run python apps/web/manage.py migrate

# Create new migrations
makemigrations *ARGS:
    doppler run -- uv run python apps/web/manage.py makemigrations {{ARGS}}

# Create a superuser
createsuperuser:
    doppler run -- uv run python apps/web/manage.py createsuperuser

# =============================================================================
# Quality
# =============================================================================

# Run all quality checks (what CI runs)
check: lint typecheck test

# Run linter
lint:
    uv run ruff check .

# Run formatter check
format-check:
    uv run ruff format --check .

# Run type checker
typecheck:
    uv run mypy apps

# Run tests
test *ARGS:
    doppler run -- uv run pytest {{ARGS}}

# Run tests with coverage
test-cov:
    doppler run -- uv run pytest --cov=apps --cov-report=term-missing

# =============================================================================
# Formatting
# =============================================================================

# Format code
fmt:
    uv run ruff format .

# Fix linting issues
fix:
    uv run ruff check --fix .

# Format and fix everything
format: fmt fix

# =============================================================================
# Pre-commit
# =============================================================================

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Update pre-commit hooks
pre-commit-update:
    uv run pre-commit autoupdate

# =============================================================================
# Database
# =============================================================================

# Reset local database (careful!)
db-reset:
    doppler run -- uv run python apps/web/manage.py flush --no-input
    doppler run -- uv run python apps/web/manage.py migrate

# Show migration status
db-status:
    doppler run -- uv run python apps/web/manage.py showmigrations

# =============================================================================
# Django Admin
# =============================================================================

# Collect static files
collectstatic:
    doppler run -- uv run python apps/web/manage.py collectstatic --no-input

# Start new Django app
startapp NAME:
    cd apps/web && doppler run -- uv run python manage.py startapp {{NAME}}

# =============================================================================
# Workers & Sites Deployment
# =============================================================================

# Deploy intake worker to Cloudflare
deploy-worker:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Deploying intake worker..."

    # Push secrets to Cloudflare Workers
    echo "Syncing secrets to Cloudflare..."
    cd workers/intake
    doppler run -- bash -c 'echo "$NEON_DATABASE_URL" | wrangler secret put NEON_DATABASE_URL'
    doppler run -- bash -c 'echo "$INTAKE_API_KEY" | wrangler secret put INTAKE_API_KEY'

    # Deploy
    echo "Deploying worker..."
    doppler run -- wrangler deploy

    echo "Done! Worker deployed."

# Deploy a client site to Cloudflare Pages
deploy-site SITE:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Deploying site: {{SITE}}..."

    cd sites/{{SITE}}

    # Build the site
    pnpm build

    # Deploy to Cloudflare Pages
    doppler run -- wrangler pages deploy dist

    echo "Done! Site {{SITE}} deployed."

# Deploy all sites
deploy-sites:
    #!/usr/bin/env bash
    set -euo pipefail
    for site in sites/*/; do
        site_name=$(basename "$site")
        if [ "$site_name" != "_template" ]; then
            echo "Deploying $site_name..."
            just deploy-site "$site_name"
        fi
    done

# =============================================================================
# Production
# =============================================================================

# Build for production
build:
    uv build

# Check production settings
check-deploy:
    doppler run -- uv run python apps/web/manage.py check --deploy

# Full production deployment check
deploy-check:
    @echo "Checking deployment readiness..."
    @just check-secrets
    @just check-deploy
    @echo "All checks passed!"

# =============================================================================
# Utilities
# =============================================================================

# Clean Python artifacts
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Show project stats
stats:
    @echo "Python files:"
    @find apps -name "*.py" | wc -l
    @echo "Lines of Python:"
    @find apps -name "*.py" -exec cat {} + | wc -l
