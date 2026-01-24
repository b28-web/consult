/**
 * Menu data fetching and types
 *
 * Fetches menu data from Django API at build time.
 * Falls back to mock data in development.
 */

// Types matching the Django API response
export interface Modifier {
  id: number;
  name: string;
  price_adjustment: string;
  is_available: boolean;
}

export interface ModifierGroup {
  id: number;
  name: string;
  min_selections: number;
  max_selections: number;
  modifiers: Modifier[];
}

export interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: string;
  image_url: string;
  is_available: boolean;
  is_vegetarian: boolean;
  is_vegan: boolean;
  is_gluten_free: boolean;
  allergens: string[];
  modifier_groups: ModifierGroup[];
}

export interface MenuCategory {
  id: number;
  name: string;
  description: string;
  items: MenuItem[];
}

export interface Menu {
  id: number;
  name: string;
  description: string;
  available_start: string | null;
  available_end: string | null;
  categories: MenuCategory[];
}

export interface MenuResponse {
  menus: Menu[];
  source: "pos" | "static";
  last_synced_at: string | null;
}

/**
 * Fetch menu data from the API
 *
 * In development without PUBLIC_API_URL, returns mock data.
 * At build time, fetches from the configured API.
 */
export async function fetchMenu(slug: string): Promise<MenuResponse> {
  const apiUrl = import.meta.env.PUBLIC_API_URL;

  // Development fallback: use mock data
  if (!apiUrl) {
    console.log("[menu] No PUBLIC_API_URL, using mock data");
    const mockData = await import("../data/mock-menu.json");
    return mockData.default as MenuResponse;
  }

  // Production: fetch from API
  const url = `${apiUrl}/api/clients/${slug}/menu`;
  console.log(`[menu] Fetching from ${url}`);

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch menu: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Get all categories across all menus (flattened)
 */
export function getAllCategories(menus: Menu[]): MenuCategory[] {
  return menus.flatMap((menu) => menu.categories);
}

/**
 * Get all items across all categories (flattened)
 */
export function getAllItems(categories: MenuCategory[]): MenuItem[] {
  return categories.flatMap((cat) => cat.items);
}
