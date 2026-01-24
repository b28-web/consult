/**
 * Cart state management using nanostores
 *
 * Stores cart data in localStorage for persistence across page navigation.
 * No login required - cart persists for the session.
 */

import { persistentAtom } from "@nanostores/persistent";
import { computed } from "nanostores";

// Cart item types
export interface CartModifierSelection {
  id: number;
  name: string;
  priceAdjustment: number;
}

export interface CartModifierGroup {
  groupId: number;
  groupName: string;
  selections: CartModifierSelection[];
}

export interface CartItem {
  id: string; // Unique cart item ID (UUID)
  menuItemId: number; // MenuItem.id from API
  name: string;
  basePrice: number; // Base price without modifiers
  quantity: number;
  modifiers: CartModifierGroup[];
  specialInstructions: string;
}

export type OrderType = "pickup" | "delivery";

export interface CartState {
  items: CartItem[];
  orderType: OrderType;
  scheduledTime: string | null; // ISO string or null for ASAP
  specialInstructions: string;
  tip: number;
}

// Tip preset percentages
export const TIP_PRESETS = [15, 18, 20, 25] as const;

// Default cart state
const DEFAULT_CART: CartState = {
  items: [],
  orderType: "pickup",
  scheduledTime: null,
  specialInstructions: "",
  tip: 0,
};

// Persistent cart store
export const cart = persistentAtom<CartState>(
  "restaurant-cart",
  DEFAULT_CART,
  {
    encode: JSON.stringify,
    decode: JSON.parse,
  }
);

// Computed: Total item count (including quantities)
export const cartItemCount = computed(cart, (state) =>
  state.items.reduce((sum, item) => sum + item.quantity, 0)
);

// Computed: Calculate price for a single cart item (including modifiers)
export function calculateItemPrice(item: CartItem): number {
  const modifierTotal = item.modifiers.reduce(
    (sum, group) =>
      sum + group.selections.reduce((s, mod) => s + mod.priceAdjustment, 0),
    0
  );
  return (item.basePrice + modifierTotal) * item.quantity;
}

// Computed: Subtotal (before tax and tip)
export const cartSubtotal = computed(cart, (state) =>
  state.items.reduce((sum, item) => sum + calculateItemPrice(item), 0)
);

// Computed: Estimated tax (8.5% - will be confirmed by backend)
export const ESTIMATED_TAX_RATE = 0.085;
export const cartTax = computed(
  cartSubtotal,
  (subtotal) => subtotal * ESTIMATED_TAX_RATE
);

// Computed: Total (subtotal + tax + tip)
export const cartTotal = computed(cart, (state) => {
  const subtotal = state.items.reduce(
    (sum, item) => sum + calculateItemPrice(item),
    0
  );
  const tax = subtotal * ESTIMATED_TAX_RATE;
  return subtotal + tax + state.tip;
});

// Generate a unique ID for cart items
function generateId(): string {
  return crypto.randomUUID();
}

// Actions

/**
 * Add an item to the cart
 */
export function addToCart(item: Omit<CartItem, "id">): void {
  const current = cart.get();
  cart.set({
    ...current,
    items: [...current.items, { ...item, id: generateId() }],
  });
}

/**
 * Update quantity of an item in the cart
 * Removes item if quantity becomes 0 or negative
 */
export function updateQuantity(itemId: string, quantity: number): void {
  if (quantity <= 0) {
    removeFromCart(itemId);
    return;
  }

  const current = cart.get();
  cart.set({
    ...current,
    items: current.items.map((item) =>
      item.id === itemId ? { ...item, quantity } : item
    ),
  });
}

/**
 * Increment item quantity by 1
 */
export function incrementQuantity(itemId: string): void {
  const current = cart.get();
  const item = current.items.find((i) => i.id === itemId);
  if (item) {
    updateQuantity(itemId, item.quantity + 1);
  }
}

/**
 * Decrement item quantity by 1
 */
export function decrementQuantity(itemId: string): void {
  const current = cart.get();
  const item = current.items.find((i) => i.id === itemId);
  if (item) {
    updateQuantity(itemId, item.quantity - 1);
  }
}

/**
 * Remove an item from the cart
 */
export function removeFromCart(itemId: string): void {
  const current = cart.get();
  cart.set({
    ...current,
    items: current.items.filter((item) => item.id !== itemId),
  });
}

/**
 * Update special instructions for an item
 */
export function updateItemInstructions(
  itemId: string,
  instructions: string
): void {
  const current = cart.get();
  cart.set({
    ...current,
    items: current.items.map((item) =>
      item.id === itemId ? { ...item, specialInstructions: instructions } : item
    ),
  });
}

/**
 * Clear all items from the cart
 */
export function clearCart(): void {
  cart.set(DEFAULT_CART);
}

/**
 * Set the order type (pickup or delivery)
 */
export function setOrderType(orderType: OrderType): void {
  cart.set({ ...cart.get(), orderType });
}

/**
 * Set the scheduled time (null for ASAP)
 */
export function setScheduledTime(time: string | null): void {
  cart.set({ ...cart.get(), scheduledTime: time });
}

/**
 * Set the tip amount
 */
export function setTip(amount: number): void {
  cart.set({ ...cart.get(), tip: Math.max(0, amount) });
}

/**
 * Set tip as a percentage of subtotal
 */
export function setTipPercentage(percentage: number): void {
  const subtotal = cartSubtotal.get();
  const tip = Math.round(subtotal * (percentage / 100) * 100) / 100;
  setTip(tip);
}

/**
 * Set order-level special instructions
 */
export function setOrderInstructions(instructions: string): void {
  cart.set({ ...cart.get(), specialInstructions: instructions });
}

/**
 * Check if a menu item can be added to cart based on availability
 */
export function canAddToCart(
  menuItemId: number,
  availability: Record<string, boolean>
): boolean {
  // If item not in availability map, assume available
  const key = menuItemId.toString();
  return availability[key] !== false;
}

/**
 * Get items that are no longer available
 * Call this when availability updates to notify user
 */
export function getUnavailableCartItems(
  availability: Record<string, boolean>
): CartItem[] {
  const current = cart.get();
  return current.items.filter(
    (item) => availability[item.menuItemId.toString()] === false
  );
}

/**
 * Remove all unavailable items from cart
 */
export function removeUnavailableItems(
  availability: Record<string, boolean>
): CartItem[] {
  const unavailable = getUnavailableCartItems(availability);
  if (unavailable.length > 0) {
    const current = cart.get();
    const unavailableIds = new Set(unavailable.map((i) => i.id));
    cart.set({
      ...current,
      items: current.items.filter((item) => !unavailableIds.has(item.id)),
    });
  }
  return unavailable;
}

/**
 * Check if cart is empty
 */
export function isCartEmpty(): boolean {
  return cart.get().items.length === 0;
}

/**
 * Get cart item by ID
 */
export function getCartItem(itemId: string): CartItem | undefined {
  return cart.get().items.find((item) => item.id === itemId);
}

/**
 * Format price for display
 */
export function formatPrice(cents: number): string {
  return `$${cents.toFixed(2)}`;
}
