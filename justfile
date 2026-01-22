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
    INFRA_MISSING=()
    for secret in HETZNER_API_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_ZONE_ID SSH_PUBLIC_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            warn "$secret (not set)"
            INFRA_MISSING+=("$secret")
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

    # Flag to track if user already opted in to infra setup
    INFRA_SETUP_REQUESTED=false

    if [ ${#MISSING[@]} -eq 0 ]; then
        success "All required secrets are configured for local development"
        echo ""

        # Check if infrastructure secrets are missing and offer to configure them
        if [ ${#INFRA_MISSING[@]} -gt 0 ]; then
            echo -e "${YELLOW}Missing ${#INFRA_MISSING[@]} infrastructure secret(s): ${INFRA_MISSING[*]}${NC}"
            echo ""
            echo "These are needed for deploying infrastructure with Pulumi."
            echo ""
            if prompt_yes_no "Would you like to configure infrastructure secrets now?"; then
                # Continue to Step 5 (Infrastructure Secrets)
                INFRA_SETUP_REQUESTED=true
            else
                echo ""
                echo "Skipped infrastructure setup."
                echo ""
                echo "Next steps for local development:"
                echo "  ${BOLD}just dev${NC}             # Start Django dev server"
                echo "  ${BOLD}just test-local${NC}      # Run full integration tests"
                echo ""
                echo "To configure infrastructure secrets later:"
                echo "  ${BOLD}just setup-infra${NC}     # Run this wizard again"
                exit 0
            fi
        else
            header "All Done!"
            success "All secrets configured!"
            echo ""
            echo "Local development:"
            echo "  ${BOLD}just dev${NC}             # Start Django dev server"
            echo "  ${BOLD}just test-local${NC}      # Run full integration tests"
            echo ""
            echo "Infrastructure deployment:"
            echo "  ${BOLD}just infra-preview${NC}   # Preview infrastructure changes"
            echo "  ${BOLD}just infra-up${NC}        # Deploy infrastructure"
            exit 0
        fi
    fi

    # Only show Step 3 and 4 if there are missing required secrets
    if [ ${#MISSING[@]} -gt 0 ]; then

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

    fi  # End of "if MISSING has elements"

    # =========================================================================
    header "Step 5: Infrastructure Secrets (Pulumi)"
    # =========================================================================

    # Determine if we should configure infra secrets
    CONFIGURE_INFRA=false
    if [ "$INFRA_SETUP_REQUESTED" = true ]; then
        # User already opted in from the early status check
        CONFIGURE_INFRA=true
    else
        echo "These secrets are needed to deploy infrastructure with Pulumi."
        echo "Skip this section if you only need local development."
        echo ""

        if prompt_yes_no "Configure infrastructure deployment secrets?" "n"; then
            CONFIGURE_INFRA=true
        else
            echo "Skipped infrastructure secrets."
        fi
    fi

    if [ "$CONFIGURE_INFRA" = true ]; then
        # HETZNER_API_TOKEN
        if ! check_secret "HETZNER_API_TOKEN"; then
            echo ""
            echo -e "${BOLD}HETZNER_API_TOKEN${NC} - Hetzner Cloud API token"
            info "Used by Pulumi to provision servers and networks"
            echo ""
            echo -e "${BOLD}To get this:${NC}"
            echo "  1. Go to: ${BLUE}https://console.hetzner.cloud${NC}"
            echo "  2. Select your project (or create one)"
            echo "  3. Go to: ${BOLD}Security → API Tokens → Generate API Token${NC}"
            echo "  4. Name it: ${BOLD}consult-pulumi${NC}"
            echo "  5. Select: ${BOLD}Read & Write${NC}"
            echo ""
            read -sp "Enter Hetzner API token (hidden): " HETZNER_TOKEN
            echo ""
            if [ -n "$HETZNER_TOKEN" ]; then
                set_secret "HETZNER_API_TOKEN" "$HETZNER_TOKEN"
            else
                warn "Skipped. Set manually: doppler secrets set HETZNER_API_TOKEN=..."
            fi
        else
            success "HETZNER_API_TOKEN already set"
        fi

        # CLOUDFLARE_API_TOKEN
        if ! check_secret "CLOUDFLARE_API_TOKEN"; then
            echo ""
            echo -e "${BOLD}CLOUDFLARE_API_TOKEN${NC} - Cloudflare API token"
            info "Used by Pulumi for DNS, Pages, and Workers"
            echo ""
            echo -e "${BOLD}To get this:${NC}"
            echo "  1. Go to: ${BLUE}https://dash.cloudflare.com/profile/api-tokens${NC}"
            echo "  2. Click: ${BOLD}Create Token${NC}"
            echo "  3. Use template: ${BOLD}Edit zone DNS${NC} (then add more permissions)"
            echo "  4. Add permissions:"
            echo "     - Zone / DNS / Edit"
            echo "     - Zone / Zone / Read"
            echo "     - Account / Cloudflare Pages / Edit"
            echo "     - Account / Workers Scripts / Edit"
            echo "  5. Zone Resources: ${BOLD}Include / Specific zone / your-domain.com${NC}"
            echo ""
            read -sp "Enter Cloudflare API token (hidden): " CF_TOKEN
            echo ""
            if [ -n "$CF_TOKEN" ]; then
                set_secret "CLOUDFLARE_API_TOKEN" "$CF_TOKEN"
            else
                warn "Skipped. Set manually: doppler secrets set CLOUDFLARE_API_TOKEN=..."
            fi
        else
            success "CLOUDFLARE_API_TOKEN already set"
        fi

        # CLOUDFLARE_ACCOUNT_ID
        if ! check_secret "CLOUDFLARE_ACCOUNT_ID"; then
            echo ""
            echo -e "${BOLD}CLOUDFLARE_ACCOUNT_ID${NC} - Your Cloudflare account ID"
            info "Found in the URL or sidebar of your Cloudflare dashboard"
            echo ""
            echo -e "${BOLD}To find this:${NC}"
            echo "  1. Go to: ${BLUE}https://dash.cloudflare.com${NC}"
            echo "  2. Select your domain"
            echo "  3. Look in the right sidebar under ${BOLD}API${NC}"
            echo "  4. Copy ${BOLD}Account ID${NC}"
            echo ""
            read -p "Enter Cloudflare Account ID: " CF_ACCOUNT_ID
            if [ -n "$CF_ACCOUNT_ID" ]; then
                set_secret "CLOUDFLARE_ACCOUNT_ID" "$CF_ACCOUNT_ID"
            else
                warn "Skipped. Set manually: doppler secrets set CLOUDFLARE_ACCOUNT_ID=..."
            fi
        else
            success "CLOUDFLARE_ACCOUNT_ID already set"
        fi

        # CLOUDFLARE_ZONE_ID
        if ! check_secret "CLOUDFLARE_ZONE_ID"; then
            echo ""
            echo -e "${BOLD}CLOUDFLARE_ZONE_ID${NC} - Zone ID for your domain"
            info "Each domain has a unique zone ID"
            echo ""
            echo -e "${BOLD}To find this:${NC}"
            echo "  1. Go to: ${BLUE}https://dash.cloudflare.com${NC}"
            echo "  2. Select your domain"
            echo "  3. Look in the right sidebar under ${BOLD}API${NC}"
            echo "  4. Copy ${BOLD}Zone ID${NC}"
            echo ""
            read -p "Enter Cloudflare Zone ID: " CF_ZONE_ID
            if [ -n "$CF_ZONE_ID" ]; then
                set_secret "CLOUDFLARE_ZONE_ID" "$CF_ZONE_ID"
            else
                warn "Skipped. Set manually: doppler secrets set CLOUDFLARE_ZONE_ID=..."
            fi
        else
            success "CLOUDFLARE_ZONE_ID already set"
        fi

        # SSH_PUBLIC_KEY
        if ! check_secret "SSH_PUBLIC_KEY"; then
            echo ""
            echo -e "${BOLD}SSH_PUBLIC_KEY${NC} - SSH public key for server access"
            info "Will be added to provisioned servers for SSH access"
            echo ""

            # Check for existing SSH keys
            if [ -f "$HOME/.ssh/id_ed25519.pub" ]; then
                echo "Found existing key: ~/.ssh/id_ed25519.pub"
                if prompt_yes_no "Use this key?"; then
                    SSH_KEY=$(cat "$HOME/.ssh/id_ed25519.pub")
                    set_secret "SSH_PUBLIC_KEY" "$SSH_KEY"
                fi
            elif [ -f "$HOME/.ssh/id_rsa.pub" ]; then
                echo "Found existing key: ~/.ssh/id_rsa.pub"
                if prompt_yes_no "Use this key?"; then
                    SSH_KEY=$(cat "$HOME/.ssh/id_rsa.pub")
                    set_secret "SSH_PUBLIC_KEY" "$SSH_KEY"
                fi
            else
                echo "No SSH key found at ~/.ssh/id_ed25519.pub or ~/.ssh/id_rsa.pub"
                echo ""
                if prompt_yes_no "Generate a new SSH key?"; then
                    ssh-keygen -t ed25519 -f "$HOME/.ssh/consult_deploy" -N "" -C "consult-deploy"
                    SSH_KEY=$(cat "$HOME/.ssh/consult_deploy.pub")
                    set_secret "SSH_PUBLIC_KEY" "$SSH_KEY"
                    success "Generated new key: ~/.ssh/consult_deploy"
                else
                    echo "Paste your SSH public key (single line):"
                    read -p "> " SSH_KEY
                    if [ -n "$SSH_KEY" ]; then
                        set_secret "SSH_PUBLIC_KEY" "$SSH_KEY"
                    else
                        warn "Skipped."
                    fi
                fi
            fi
        else
            success "SSH_PUBLIC_KEY already set"
        fi

        # DOMAIN
        if ! check_secret "DOMAIN"; then
            echo ""
            echo -e "${BOLD}DOMAIN${NC} - Primary domain for the platform"
            info "e.g., consult.example.com or example.com"
            echo ""
            read -p "Enter your domain: " DOMAIN
            if [ -n "$DOMAIN" ]; then
                set_secret "DOMAIN" "$DOMAIN"
            else
                warn "Skipped. Set manually: doppler secrets set DOMAIN=..."
            fi
        else
            success "DOMAIN already set"
        fi
    fi

    # =========================================================================
    header "Step 6: Pulumi Stack Configuration"
    # =========================================================================

    # Check if Pulumi is available
    if ! command -v pulumi &> /dev/null; then
        warn "Pulumi CLI not installed. Skipping stack configuration."
        echo "Install Pulumi or run 'flox activate' to get it."
    elif check_secret "HETZNER_API_TOKEN" && check_secret "CLOUDFLARE_API_TOKEN"; then
        echo "Pulumi uses encrypted config for provider secrets."
        echo "This syncs your Doppler secrets to Pulumi stacks."
        echo ""

        if prompt_yes_no "Configure Pulumi stacks with your secrets?" "n"; then
            cd infra

            # Initialize if needed
            if [ ! -d ".venv" ]; then
                echo "Initializing Pulumi environment..."
                python3 -m venv .venv
                .venv/bin/pip install -q -r requirements.txt
            fi

            # Get secrets from Doppler
            HETZNER_TOKEN=$(doppler secrets get HETZNER_API_TOKEN --plain)
            CF_TOKEN=$(doppler secrets get CLOUDFLARE_API_TOKEN --plain)
            CF_ACCOUNT=$(doppler secrets get CLOUDFLARE_ACCOUNT_ID --plain 2>/dev/null || echo "")
            CF_ZONE=$(doppler secrets get CLOUDFLARE_ZONE_ID --plain 2>/dev/null || echo "")
            DOMAIN=$(doppler secrets get DOMAIN --plain 2>/dev/null || echo "")

            # Configure dev stack
            if pulumi stack ls 2>/dev/null | grep -q "dev"; then
                echo "Configuring dev stack..."
                pulumi config set --secret hcloud:token "$HETZNER_TOKEN" --stack dev
                pulumi config set --secret cloudflare:apiToken "$CF_TOKEN" --stack dev
                if [ -n "$CF_ACCOUNT" ]; then
                    pulumi config set cloudflare_account_id "$CF_ACCOUNT" --stack dev
                fi
                if [ -n "$CF_ZONE" ]; then
                    pulumi config set cloudflare_zone_id "$CF_ZONE" --stack dev
                fi
                if [ -n "$DOMAIN" ]; then
                    pulumi config set domain "$DOMAIN" --stack dev
                fi
                success "Dev stack configured"
            else
                warn "Dev stack not found. Run 'just infra-init' first."
            fi

            # Configure prod stack
            if pulumi stack ls 2>/dev/null | grep -q "prod"; then
                if prompt_yes_no "Also configure prod stack with the same secrets?"; then
                    echo "Configuring prod stack..."
                    pulumi config set --secret hcloud:token "$HETZNER_TOKEN" --stack prod
                    pulumi config set --secret cloudflare:apiToken "$CF_TOKEN" --stack prod
                    if [ -n "$CF_ACCOUNT" ]; then
                        pulumi config set cloudflare_account_id "$CF_ACCOUNT" --stack prod
                    fi
                    if [ -n "$CF_ZONE" ]; then
                        pulumi config set cloudflare_zone_id "$CF_ZONE" --stack prod
                    fi
                    if [ -n "$DOMAIN" ]; then
                        pulumi config set domain "$DOMAIN" --stack prod
                    fi
                    success "Prod stack configured"
                fi
            fi

            cd ..
        else
            echo "Skipped Pulumi configuration."
            echo "Run 'just infra-secrets' later to configure manually."
        fi
    else
        info "Skipping Pulumi configuration (infrastructure secrets not set)"
    fi

    # =========================================================================
    header "Final Status"
    # =========================================================================

    STILL_MISSING=()

    echo "Required (local development):"
    for secret in SECRET_KEY DEBUG ALLOWED_HOSTS DATABASE_URL NEON_DATABASE_URL INTAKE_API_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            error "$secret"
            STILL_MISSING+=("$secret")
        fi
    done

    echo ""
    echo "Infrastructure (deployment):"
    for secret in HETZNER_API_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_ZONE_ID DOMAIN SSH_PUBLIC_KEY; do
        if check_secret "$secret"; then
            success "$secret"
        else
            warn "$secret (optional)"
        fi
    done

    echo ""
    if [ ${#STILL_MISSING[@]} -eq 0 ]; then
        echo -e "${GREEN}${BOLD}All required secrets configured!${NC}"
        echo ""
        echo "Local development:"
        echo -e "  ${BOLD}just migrate${NC}         # Run database migrations"
        echo -e "  ${BOLD}just dev${NC}             # Start Django dev server"
        echo -e "  ${BOLD}just test-local${NC}      # Run integration tests"
        echo ""
        if check_secret "HETZNER_API_TOKEN" && check_secret "CLOUDFLARE_API_TOKEN"; then
            echo "Infrastructure deployment:"
            echo -e "  ${BOLD}just infra-preview${NC}   # Preview infrastructure changes"
            echo -e "  ${BOLD}just infra-up${NC}        # Deploy infrastructure"
        else
            echo "For infrastructure deployment, re-run this wizard"
            echo "and configure Hetzner/Cloudflare secrets."
        fi
    else
        echo -e "${YELLOW}Still missing: ${STILL_MISSING[*]}${NC}"
        echo ""
        echo -e "Run ${BOLD}just setup-infra${NC} again after setting them."
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

# Run full local test suite (native processes, not Docker)
# Uses --remote mode for worker to avoid workerd TLS issues with Neon
test-local:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "╔═══════════════════════════════════════╗"
    echo "║     Local Integration Tests           ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""

    # Check wrangler auth for --remote mode
    if ! (cd workers/intake && pnpm wrangler whoami &>/dev/null); then
        echo "Worker tests require Cloudflare authentication for --remote mode."
        echo "Run: cd workers/intake && pnpm wrangler login"
        echo ""
        echo "Or to skip worker tests, run: just test"
        exit 1
    fi

    # Create PID directory
    mkdir -p .pids

    # Cleanup on exit
    cleanup() {
        echo ""
        echo "Cleaning up..."
        for pidfile in .pids/*.pid; do
            if [ -f "$pidfile" ]; then
                pid=$(cat "$pidfile")
                kill "$pid" 2>/dev/null || true
                pkill -P "$pid" 2>/dev/null || true
                rm -f "$pidfile"
            fi
        done
        rm -rf .pids
    }
    trap cleanup EXIT

    # Start Django
    echo "Starting Django on :8000..."
    doppler run -- uv run python apps/web/manage.py runserver 8000 > .pids/django.log 2>&1 &
    echo $! > .pids/django.pid

    # Start Worker with --remote mode (avoids workerd TLS issues with Neon)
    echo "Starting Worker on :8787 (remote mode)..."
    cd workers/intake
    doppler run -- sh -c 'echo "NEON_DATABASE_URL=$NEON_DATABASE_URL" > .dev.vars && echo "INTAKE_API_KEY=$INTAKE_API_KEY" >> .dev.vars'
    pnpm wrangler dev --remote --port 8787 > ../../.pids/worker.log 2>&1 &
    echo $! > ../../.pids/worker.pid
    cd ../..

    # Wait for services to be ready (remote mode takes longer)
    echo "Waiting for services (remote mode may take 10-20s)..."
    for i in {1..45}; do
        DJANGO_OK=$(curl -sf http://localhost:8000/admin/login/ > /dev/null 2>&1 && echo "yes" || echo "no")
        WORKER_OK=$(curl -sf http://localhost:8787/health > /dev/null 2>&1 && echo "yes" || echo "no")

        if [ "$DJANGO_OK" = "yes" ] && [ "$WORKER_OK" = "yes" ]; then
            echo "All services ready!"
            break
        fi

        if [ $i -eq 45 ]; then
            echo "Timeout waiting for services"
            echo "Django: $DJANGO_OK, Worker: $WORKER_OK"
            echo "--- Django logs ---"
            tail -20 .pids/django.log || true
            echo "--- Worker logs ---"
            tail -20 .pids/worker.log || true
            exit 1
        fi

        sleep 1
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
# Pre-Deploy Validation (Dagger)
# =============================================================================

# Run full pre-deploy validation via Dagger
pre-deploy:
    cd dagger && dagger call pre-deploy --source=..

# Run full pre-deploy validation with JSON output
pre-deploy-json:
    cd dagger && dagger call pre-deploy --source=.. --json-output

# Run only build validation
pre-deploy-build:
    cd dagger && dagger call build-all --source=..

# Run only quality checks
pre-deploy-quality:
    cd dagger && dagger call quality-all --source=..

# Run only integration tests
pre-deploy-integration:
    cd dagger && dagger call integration-all --source=..

# Build specific components
pre-deploy-django:
    cd dagger && dagger call build-django --source=..

pre-deploy-worker:
    cd dagger && dagger call build-worker --source=..

pre-deploy-site SITE="coffee-shop":
    cd dagger && dagger call build-site --source=.. --name={{SITE}}

# Run specific quality checks via Dagger
dagger-lint:
    cd dagger && dagger call lint --source=..

dagger-typecheck:
    cd dagger && dagger call typecheck --source=..

dagger-test:
    cd dagger && dagger call test --source=..

# =============================================================================
# Unified Deployment (Doppler → Dagger → Pulumi → Apps)
# =============================================================================

# Full deployment pipeline: validate → provision → deploy
deploy ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "═══════════════════════════════════════════════════════════"
    echo "  Deploying to {{ENV}}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    just deploy-validate {{ENV}}
    just deploy-infra {{ENV}}
    just deploy-apps {{ENV}}
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Deployment to {{ENV}} complete!"
    echo "═══════════════════════════════════════════════════════════"

# Step 1: Validate (Dagger pre-deploy checks)
deploy-validate ENV="dev":
    @echo "→ Running pre-deploy validation..."
    cd dagger && dagger call pre-deploy --source=..

# Step 2: Provision infrastructure (Pulumi)
deploy-infra ENV="dev":
    @echo "→ Provisioning infrastructure ({{ENV}})..."
    cd infra && doppler run --config {{ENV}} -- pulumi up --stack {{ENV}} --yes

# Step 3: Deploy applications
deploy-apps ENV="dev":
    @echo "→ Deploying applications..."
    just deploy-worker-to {{ENV}}
    just deploy-sites-to {{ENV}}
    just deploy-django-to {{ENV}}

# Deploy worker to Cloudflare
deploy-worker-to ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "  Deploying intake worker..."
    cd workers/intake
    doppler run --config {{ENV}} -- bash -c 'echo "$NEON_DATABASE_URL" | pnpm wrangler secret put NEON_DATABASE_URL'
    doppler run --config {{ENV}} -- bash -c 'echo "$INTAKE_API_KEY" | pnpm wrangler secret put INTAKE_API_KEY'
    doppler run --config {{ENV}} -- pnpm wrangler deploy
    echo "  ✓ Worker deployed"

# Deploy all sites to Cloudflare Pages
deploy-sites-to ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    for site in sites/*/; do
        name=$(basename "$site")
        [[ "$name" == "_template" ]] && continue
        echo "  Deploying site: $name..."
        cd "$site"
        pnpm build
        doppler run --config {{ENV}} -- pnpm wrangler pages deploy dist --project-name="$name"
        cd - > /dev/null
    done
    echo "  ✓ Sites deployed"

# Deploy Django to Hetzner
deploy-django-to ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "  Deploying Django to Hetzner..."
    SERVER_IP=$(cd infra && doppler run --config {{ENV}} -- pulumi stack output django_server_ip --stack {{ENV}})
    if [ -z "$SERVER_IP" ]; then
        echo "  ✗ Could not get server IP from Pulumi outputs"
        exit 1
    fi
    echo "  Server: $SERVER_IP"
    ssh -o StrictHostKeyChecking=accept-new ubuntu@"$SERVER_IP" 'cd /opt/consult && ./deploy.sh'
    echo "  ✓ Django deployed"

# =============================================================================
# CI Deployment (Non-interactive, for GitHub Actions / automation)
# =============================================================================

# CI: Full deployment (validate → infra → apps)
deploy-ci ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy: {{ENV}} (full pipeline)"
    echo "═══════════════════════════════════════════════════════════"
    just deploy-validate {{ENV}}
    just deploy-infra {{ENV}}
    just deploy-apps {{ENV}}
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy complete!"
    echo "═══════════════════════════════════════════════════════════"

# CI: Deploy apps only (skip validation and infrastructure)
deploy-ci-apps ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy: {{ENV}} (apps only)"
    echo "═══════════════════════════════════════════════════════════"
    just deploy-apps {{ENV}}
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy (apps) complete!"
    echo "═══════════════════════════════════════════════════════════"

# CI: Deploy with infra but skip validation (use with caution)
deploy-ci-no-validate ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy: {{ENV}} (skip validation)"
    echo "═══════════════════════════════════════════════════════════"
    just deploy-infra {{ENV}}
    just deploy-apps {{ENV}}
    echo "═══════════════════════════════════════════════════════════"
    echo "  CI Deploy complete!"
    echo "═══════════════════════════════════════════════════════════"

# CI: Validate only (useful for PR checks)
deploy-ci-validate:
    @echo "Running pre-deploy validation..."
    cd dagger && dagger call pre-deploy --source=..
    @echo "Validation passed!"

# =============================================================================
# Infrastructure (Pulumi with Doppler)
# =============================================================================

# Preview infrastructure changes
infra-preview ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi preview --stack {{ENV}}

# Apply infrastructure changes
infra-up ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi up --stack {{ENV}}

# Apply infrastructure changes (auto-approve, for CI)
infra-up-yes ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi up --stack {{ENV}} --yes

# Destroy infrastructure (careful!)
infra-destroy ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi destroy --stack {{ENV}}

# Show infrastructure outputs
infra-outputs ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi stack output --stack {{ENV}} --json

# Refresh infrastructure state
infra-refresh ENV="dev":
    cd infra && doppler run --config {{ENV}} -- pulumi refresh --stack {{ENV}}

# Initialize Pulumi infrastructure
infra-init:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Initializing Pulumi infrastructure..."
    cd infra

    # Create virtual environment if needed
    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv .venv
    fi

    # Install dependencies
    echo "Installing Pulumi providers..."
    .venv/bin/pip install -r requirements.txt

    # Initialize stacks if they don't exist
    echo "Checking stacks..."
    if ! pulumi stack ls 2>/dev/null | grep -q "dev"; then
        echo "Creating dev stack..."
        pulumi stack init dev
    fi
    if ! pulumi stack ls 2>/dev/null | grep -q "prod"; then
        echo "Creating prod stack..."
        pulumi stack init prod
    fi

    echo ""
    echo "Infrastructure initialized!"
    echo ""
    echo "Next steps:"
    echo "  1. Configure provider secrets:"
    echo "     pulumi config set --secret hcloud:token YOUR_HETZNER_TOKEN --stack dev"
    echo "     pulumi config set --secret cloudflare:apiToken YOUR_CF_TOKEN --stack dev"
    echo ""
    echo "  2. Update stack config (infra/Pulumi.dev.yaml):"
    echo "     - Set domain to your domain"
    echo "     - Set cloudflare_account_id"
    echo "     - Set cloudflare_zone_id"
    echo ""
    echo "  3. Preview changes:"
    echo "     just infra-preview"

# Configure infrastructure secrets interactively
infra-secrets STACK="dev":
    #!/usr/bin/env bash
    set -euo pipefail
    cd infra

    echo "Configuring secrets for stack: {{STACK}}"
    echo ""

    # Hetzner token
    echo "Enter Hetzner API token (from https://console.hetzner.cloud):"
    read -s HCLOUD_TOKEN
    pulumi config set --secret hcloud:token "$HCLOUD_TOKEN" --stack {{STACK}}
    echo "✓ Hetzner token set"

    # Cloudflare token
    echo ""
    echo "Enter Cloudflare API token (from https://dash.cloudflare.com/profile/api-tokens):"
    read -s CF_TOKEN
    pulumi config set --secret cloudflare:apiToken "$CF_TOKEN" --stack {{STACK}}
    echo "✓ Cloudflare token set"

    echo ""
    echo "Secrets configured for {{STACK}} stack."
    echo "Now update infra/Pulumi.{{STACK}}.yaml with your domain and zone IDs."

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
