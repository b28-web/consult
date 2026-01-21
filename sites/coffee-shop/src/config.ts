/**
 * Site Configuration
 *
 * This file defines all site-specific configuration.
 * Copy _template/ to create a new site, then customize this file.
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
  };
}

// ============================================================================
// CUSTOMIZE BELOW FOR EACH SITE
// ============================================================================

export const config: SiteConfig = {
  client: {
    slug: "coffee-shop",
    name: "The Daily Grind",
    tagline: "Your neighborhood coffee destination",
    phone: "(555) 234-5678",
    email: "hello@thedailygrind.coffee",
    address: "456 Roast Ave, Brewtown, CA 90210",
  },
  intake: {
    formUrl: "https://intake.consult.io/coffee-shop/form",
  },
  services: [
    {
      name: "Coffee Bar",
      slug: "coffee-bar",
      description:
        "Expertly crafted espresso drinks, pour-overs, and cold brews made from locally roasted beans.",
    },
    {
      name: "Pastries",
      slug: "pastries",
      description:
        "Fresh-baked croissants, muffins, and seasonal treats made daily in-house.",
    },
    {
      name: "Catering",
      slug: "catering",
      description:
        "Coffee service and pastry platters for your office meetings, events, and gatherings.",
    },
    {
      name: "Event Space",
      slug: "event-space",
      description:
        "Book our cozy back room for private events, book clubs, or small gatherings.",
    },
  ],
  social: {
    instagram: "https://instagram.com/thedailygrind",
    facebook: "https://facebook.com/thedailygrindcoffee",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Menu", href: "/services" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ],
};
