/**
 * Katie's Sushi - Site Configuration
 *
 * Inspired by Ebiko SF - grab-and-go sushi, clean presentation, affordable.
 */

// Base config interface (shared with service sites)
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
  social: {
    facebook?: string;
    instagram?: string;
    twitter?: string;
    yelp?: string;
    tripadvisor?: string;
  };
  nav: Array<{
    label: string;
    href: string;
  }>;
  branding?: {
    primaryColor?: string;
  };
}

// Restaurant-specific hours format
export type DayHours = { open: string; close: string }[] | "closed";

// Restaurant-specific configuration
export interface RestaurantConfig extends SiteConfig {
  restaurant: {
    cuisine: string[];
    priceRange: "$" | "$$" | "$$$" | "$$$$";
    hours: {
      monday: DayHours;
      tuesday: DayHours;
      wednesday: DayHours;
      thursday: DayHours;
      friday: DayHours;
      saturday: DayHours;
      sunday: DayHours;
    };
    features: {
      dineIn: boolean;
      takeout: boolean;
      delivery: boolean;
      reservations: boolean;
      onlineOrdering: boolean;
    };
    // POS integration (optional)
    pos?: {
      provider: "toast" | "clover" | "square" | null;
      locationId: string;
    };
    // Reservation integration (optional)
    reservations?: {
      provider: "resy" | "opentable" | "yelp" | null;
      url: string;
    };
  };
}

// ============================================================================
// KATIE'S SUSHI CONFIGURATION
// ============================================================================

export const config: RestaurantConfig = {
  client: {
    slug: "katies-sushi",
    name: "Katie's Sushi",
    tagline: "Fresh grab-and-go sushi",
    phone: "(415) 555-0123",
    email: "hello@katiessushi.com",
    address: "123 Market Street, San Francisco, CA 94105",
  },
  intake: {
    formUrl: "https://intake.consult.dev/katies-sushi/form",
  },
  social: {
    instagram: "https://instagram.com/katiessushi",
    yelp: "https://yelp.com/biz/katies-sushi-sf",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "Order", href: "/checkout" },
    { label: "Contact", href: "/contact" },
  ],
  branding: {
    primaryColor: "#c41e3a", // Deep red (Japanese aesthetic)
  },
  restaurant: {
    cuisine: ["Japanese", "Sushi"],
    priceRange: "$",
    hours: {
      monday: [{ open: "11:00", close: "20:00" }],
      tuesday: [{ open: "11:00", close: "20:00" }],
      wednesday: [{ open: "11:00", close: "20:00" }],
      thursday: [{ open: "11:00", close: "20:00" }],
      friday: [{ open: "11:00", close: "21:00" }],
      saturday: [{ open: "11:00", close: "21:00" }],
      sunday: "closed",
    },
    features: {
      dineIn: false, // Grab-and-go style like Ebiko
      takeout: true,
      delivery: false,
      reservations: false,
      onlineOrdering: true,
    },
  },
};
