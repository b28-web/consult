/**
 * Restaurant Site Configuration
 *
 * Extends base SiteConfig with restaurant-specific settings.
 * Copy _template-restaurant/ to create a new restaurant site.
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
// CUSTOMIZE BELOW FOR EACH RESTAURANT
// ============================================================================

export const config: RestaurantConfig = {
  client: {
    slug: "template-restaurant",
    name: "Sample Restaurant",
    tagline: "Delicious food, made with love",
    phone: "(555) 123-4567",
    email: "hello@samplerestaurant.com",
    address: "123 Main Street, Anytown, ST 12345",
  },
  intake: {
    formUrl: "https://intake.consult.io/template-restaurant/form",
  },
  social: {
    instagram: "https://instagram.com/samplerestaurant",
    facebook: "https://facebook.com/samplerestaurant",
    yelp: "https://yelp.com/biz/sample-restaurant",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Menu", href: "/menu" },
    { label: "Contact", href: "/contact" },
  ],
  restaurant: {
    cuisine: ["American", "Burgers", "Sandwiches"],
    priceRange: "$$",
    hours: {
      monday: [{ open: "11:00", close: "21:00" }],
      tuesday: [{ open: "11:00", close: "21:00" }],
      wednesday: [{ open: "11:00", close: "21:00" }],
      thursday: [{ open: "11:00", close: "21:00" }],
      friday: [{ open: "11:00", close: "22:00" }],
      saturday: [{ open: "10:00", close: "22:00" }],
      sunday: [{ open: "10:00", close: "20:00" }],
    },
    features: {
      dineIn: true,
      takeout: true,
      delivery: false,
      reservations: false,
      onlineOrdering: true, // Enabled for cart/checkout development
    },
    // Uncomment when POS is connected
    // pos: {
    //   provider: "toast",
    //   locationId: "abc123",
    // },
  },
};
