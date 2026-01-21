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
    slug: "template",
    name: "Business Name",
    tagline: "Your tagline here",
    phone: "(555) 123-4567",
    email: "hello@example.com",
    address: "123 Main St, City, ST 12345",
  },
  intake: {
    // Worker endpoint for form submissions
    formUrl: "https://intake.consult.io/template/form",
  },
  services: [
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
  ],
  social: {
    // Add your social links
    // facebook: "https://facebook.com/...",
    // instagram: "https://instagram.com/...",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Services", href: "/services" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ],
  // Uncomment if using Cal.com for scheduling
  // calcom: {
  //   username: "your-username",
  //   eventSlug: "30min",
  // },
};
