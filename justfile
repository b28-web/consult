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

# =============================================================================
# Development
# =============================================================================

# Run Django development server
dev:
    doppler run -- uv run python apps/web/manage.py runserver

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
# Production
# =============================================================================

# Build for production
build:
    uv build

# Check production settings
check-deploy:
    doppler run -- uv run python apps/web/manage.py check --deploy

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
