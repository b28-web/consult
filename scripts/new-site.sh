#!/usr/bin/env bash
#
# Create a new client site from the template.
# Usage: ./scripts/new-site.sh
#        ./scripts/new-site.sh --slug foo --name "Foo Bar" --tagline "Best Foo" --industry coffee-shop
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$PROJECT_ROOT/sites/_template"

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get industry-specific services
get_services() {
    local industry="$1"
    case "$industry" in
        coffee-shop)
            cat << 'SERVICES'
[
    {
      name: "Coffee & Espresso",
      slug: "coffee",
      description: "Premium roasted coffee and handcrafted espresso drinks.",
    },
    {
      name: "Pastries & Food",
      slug: "pastries",
      description: "Fresh-baked pastries and light breakfast items.",
    },
    {
      name: "Catering",
      slug: "catering",
      description: "Coffee service for your office or event.",
    },
  ]
SERVICES
            ;;
        hauler)
            cat << 'SERVICES'
[
    {
      name: "Junk Removal",
      slug: "junk-removal",
      description: "Full-service junk removal for homes and businesses.",
    },
    {
      name: "Demolition",
      slug: "demolition",
      description: "Light demolition and debris removal.",
    },
    {
      name: "Cleanouts",
      slug: "cleanouts",
      description: "Estate, garage, and storage unit cleanouts.",
    },
  ]
SERVICES
            ;;
        cleaning)
            cat << 'SERVICES'
[
    {
      name: "Residential Cleaning",
      slug: "residential",
      description: "Regular house cleaning and deep cleaning services.",
    },
    {
      name: "Commercial Cleaning",
      slug: "commercial",
      description: "Office and commercial space cleaning.",
    },
    {
      name: "Move In/Out Cleaning",
      slug: "move-cleaning",
      description: "Thorough cleaning for moving transitions.",
    },
  ]
SERVICES
            ;;
        landscaper)
            cat << 'SERVICES'
[
    {
      name: "Lawn Maintenance",
      slug: "lawn",
      description: "Regular mowing, edging, and lawn care.",
    },
    {
      name: "Landscape Design",
      slug: "design",
      description: "Custom landscape design and installation.",
    },
    {
      name: "Seasonal Services",
      slug: "seasonal",
      description: "Spring cleanup, fall cleanup, and snow removal.",
    },
  ]
SERVICES
            ;;
        barber)
            cat << 'SERVICES'
[
    {
      name: "Haircuts",
      slug: "haircuts",
      description: "Classic and modern cuts for all styles.",
    },
    {
      name: "Beard Trimming",
      slug: "beard",
      description: "Professional beard shaping and trimming.",
    },
    {
      name: "Hot Towel Shave",
      slug: "shave",
      description: "Traditional straight razor shave experience.",
    },
  ]
SERVICES
            ;;
        saas)
            cat << 'SERVICES'
[
    {
      name: "Platform",
      slug: "platform",
      description: "Our core product that powers your workflow.",
    },
    {
      name: "Enterprise",
      slug: "enterprise",
      description: "Custom solutions for large organizations.",
    },
    {
      name: "Integrations",
      slug: "integrations",
      description: "Connect with the tools you already use.",
    },
  ]
SERVICES
            ;;
        agency)
            cat << 'SERVICES'
[
    {
      name: "Web Design",
      slug: "web-design",
      description: "Custom websites that convert visitors to customers.",
    },
    {
      name: "Development",
      slug: "development",
      description: "Full-stack web and mobile application development.",
    },
    {
      name: "Strategy",
      slug: "strategy",
      description: "Digital strategy and consulting services.",
    },
  ]
SERVICES
            ;;
        restaurant)
            # Note: Full restaurant sites with POS/ordering need _template-restaurant from EP-008
            cat << 'SERVICES'
[
    {
      name: "Dine In",
      slug: "dine-in",
      description: "Enjoy your meal in our welcoming dining room.",
    },
    {
      name: "Takeout",
      slug: "takeout",
      description: "Order ahead and pick up at your convenience.",
    },
    {
      name: "Catering",
      slug: "catering",
      description: "Let us cater your next event or gathering.",
    },
  ]
SERVICES
            ;;
        *)
            cat << 'SERVICES'
[
    {
      name: "Service One",
      slug: "service-one",
      description: "Description of your first service offering.",
    },
    {
      name: "Service Two",
      slug: "service-two",
      description: "Description of your second service offering.",
    },
  ]
SERVICES
            ;;
    esac
}

# Get industry-specific nav
get_nav() {
    local industry="$1"
    case "$industry" in
        hauler|barber)
            # Booking-focused industries get simpler nav
            cat << 'NAV'
[
    { label: "Home", href: "/" },
    { label: "Services", href: "/services" },
    { label: "Book Now", href: "/contact" },
  ]
NAV
            ;;
        restaurant)
            # Restaurant nav with menu focus
            cat << 'NAV'
[
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "Order", href: "/order" },
    { label: "Contact", href: "/contact" },
  ]
NAV
            ;;
        coffee-shop)
            # Cafe nav with menu
            cat << 'NAV'
[
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ]
NAV
            ;;
        *)
            cat << 'NAV'
[
    { label: "Home", href: "/" },
    { label: "Services", href: "/services" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ]
NAV
            ;;
    esac
}

# Parse command line arguments
SLUG=""
NAME=""
TAGLINE=""
INDUSTRY=""
REGISTER="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --slug)
            SLUG="$2"
            shift 2
            ;;
        --name)
            NAME="$2"
            shift 2
            ;;
        --tagline)
            TAGLINE="$2"
            shift 2
            ;;
        --industry)
            INDUSTRY="$2"
            shift 2
            ;;
        --register)
            REGISTER="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --slug SLUG         Site slug (lowercase, hyphens only)"
            echo "  --name NAME         Business name"
            echo "  --tagline TAGLINE   Business tagline"
            echo "  --industry INDUSTRY Industry type"
            echo "  --register          Also register site for deployment (adds to registry.yaml)"
            echo "  -h, --help          Show this help"
            echo ""
            echo "Industries: coffee-shop, restaurant, hauler, cleaning, landscaper, barber, saas, agency"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}  New Client Site Scaffolding${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Prompt for missing values
if [[ -z "$SLUG" ]]; then
    read -rp "Site slug (lowercase, hyphens): " SLUG
fi

if [[ -z "$NAME" ]]; then
    read -rp "Business name: " NAME
fi

if [[ -z "$TAGLINE" ]]; then
    read -rp "Tagline: " TAGLINE
fi

if [[ -z "$INDUSTRY" ]]; then
    echo "Industries: coffee-shop, restaurant, hauler, cleaning, landscaper, barber, saas, agency"
    read -rp "Industry: " INDUSTRY
fi

# Validate slug
if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]*$ ]]; then
    echo -e "${RED}Error: Slug must be lowercase letters, numbers, and hyphens, starting with a letter${NC}"
    exit 1
fi

# Check if site already exists
TARGET_DIR="$PROJECT_ROOT/sites/$SLUG"
if [[ -d "$TARGET_DIR" ]]; then
    echo -e "${RED}Error: Site already exists at sites/$SLUG${NC}"
    exit 1
fi

# Check template exists
if [[ ! -d "$TEMPLATE_DIR" ]]; then
    echo -e "${RED}Error: Template not found at sites/_template${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Creating site:${NC}"
echo "  Slug:     $SLUG"
echo "  Name:     $NAME"
echo "  Tagline:  $TAGLINE"
echo "  Industry: $INDUSTRY"
echo ""

# Copy template (excluding node_modules)
echo -e "${BLUE}Copying template...${NC}"
mkdir -p "$TARGET_DIR"
rsync -a --exclude='node_modules' --exclude='.astro' "$TEMPLATE_DIR/" "$TARGET_DIR/"

# Get services and nav for this industry
SERVICES=$(get_services "$INDUSTRY")
NAV=$(get_nav "$INDUSTRY")

# Create the new config.ts with proper values
echo -e "${BLUE}Updating config.ts...${NC}"
cat > "$TARGET_DIR/src/config.ts" << EOF
/**
 * Site Configuration
 *
 * This file defines all site-specific configuration.
 * Generated by scripts/new-site.sh
 */

export interface SiteConfig {
  client: {
    slug: string;
    name: string;
    tagline: string;
    phone?: string;
    email: string;
    address?: string;
  };
  intake: {
    formUrl: string;
  };
  services: Array<{
    name: string;
    slug: string;
    description: string;
    icon?: string;
  }>;
  social: {
    facebook?: string;
    instagram?: string;
    twitter?: string;
    linkedin?: string;
    youtube?: string;
    tiktok?: string;
  };
  nav: Array<{
    label: string;
    href: string;
  }>;
  // Cal.com integration (optional)
  calcom?: {
    username: string;
    eventSlug: string;
    /** Brand color (hex without #, e.g., "4f46e5") */
    brandColor?: string;
  };
  // Branding (optional, for integrations)
  branding?: {
    /** Primary brand color (hex without #) */
    primaryColor?: string;
  };
}

// ============================================================================
// SITE CONFIGURATION: $SLUG
// ============================================================================

export const config: SiteConfig = {
  client: {
    slug: "$SLUG",
    name: "$NAME",
    tagline: "$TAGLINE",
    phone: "(555) 123-4567",
    email: "hello@$SLUG.com",
    address: "123 Main St, City, ST 12345",
  },
  intake: {
    // Worker endpoint for form submissions
    formUrl: "https://intake.consult.io/$SLUG/form",
  },
  services: $SERVICES,
  social: {
    // Add your social links
    // facebook: "https://facebook.com/...",
    // instagram: "https://instagram.com/...",
  },
  nav: $NAV,
  // Uncomment if using Cal.com for scheduling
  // calcom: {
  //   username: "your-username",
  //   eventSlug: "30min",
  // },
};
EOF

# Update wrangler.toml
echo -e "${BLUE}Updating wrangler.toml...${NC}"
sed -i '' "s/name = \"consult-template\"/name = \"consult-$SLUG\"/" "$TARGET_DIR/wrangler.toml"

# Update package.json
echo -e "${BLUE}Updating package.json...${NC}"
sed -i '' "s/@consult\/site-template/@consult\/site-$SLUG/" "$TARGET_DIR/package.json"

# Register site if requested
if [[ "$REGISTER" == "true" ]]; then
    echo -e "${BLUE}Registering site in registry.yaml...${NC}"
    REGISTRY_FILE="$PROJECT_ROOT/sites/registry.yaml"

    # Check if already registered (shouldn't happen for new site, but be safe)
    if grep -q "^  $SLUG:" "$REGISTRY_FILE" 2>/dev/null; then
        echo -e "${YELLOW}Site already in registry${NC}"
    else
        cat >> "$REGISTRY_FILE" << EOF

  $SLUG:
    ready: true
    dev: {}
    # prod:
    #   domain: $SLUG.example.com
EOF
        echo -e "${GREEN}Site registered with ready=true${NC}"
    fi
fi

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  Site created successfully!${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo -e "Site location: ${BLUE}sites/$SLUG${NC}"
if [[ "$REGISTER" == "true" ]]; then
    echo -e "Registry:      ${GREEN}registered (ready=true)${NC}"
else
    echo -e "Registry:      ${YELLOW}not registered${NC} (run: just register-site $SLUG)"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. cd sites/$SLUG"
echo "  2. Edit src/config.ts with actual contact info"
echo "  3. Customize tailwind.config.ts colors for brand"
echo "  4. pnpm install (from repo root)"
echo "  5. pnpm --filter @consult/site-$SLUG dev"
if [[ "$REGISTER" == "true" ]]; then
    echo "  6. Deploy: just deploy-wizard dev"
else
    echo "  6. Register: just register-site $SLUG"
    echo "  7. Deploy: just deploy-wizard dev"
fi
echo ""
