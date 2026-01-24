/**
 * Checkout utilities and order preparation
 *
 * Prepares order data for submission to the API.
 * Payment integration will be added in 008-K.
 */

import { cart, type CartItem, type CartModifierGroup } from "./cart";

export interface CustomerInfo {
  name: string;
  email: string;
  phone: string;
}

export interface OrderLineItem {
  menu_item_id: number;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers: {
    group_id: number;
    group_name: string;
    selections: {
      id: number;
      name: string;
      price_adjustment: number;
    }[];
  }[];
  special_instructions: string;
}

export interface OrderSubmission {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  order_type: "pickup" | "delivery";
  scheduled_time: string | null;
  special_instructions: string;
  items: OrderLineItem[];
  subtotal: number;
  tax: number;
  tip: number;
  total: number;
}

/**
 * Calculate line item price including modifiers
 */
function calculateLineItemPrice(item: CartItem): number {
  const modifierTotal = item.modifiers.reduce(
    (sum, group) =>
      sum + group.selections.reduce((s, mod) => s + mod.priceAdjustment, 0),
    0
  );
  return item.basePrice + modifierTotal;
}

/**
 * Prepare order data for API submission
 */
export function prepareOrderSubmission(customer: CustomerInfo): OrderSubmission {
  const cartState = cart.get();
  const items = cartState.items;

  // Calculate totals
  const subtotal = items.reduce(
    (sum, item) => sum + calculateLineItemPrice(item) * item.quantity,
    0
  );
  const taxRate = 0.085; // 8.5% - should match cart.ts
  const tax = subtotal * taxRate;
  const total = subtotal + tax + cartState.tip;

  // Map cart items to order line items
  const lineItems: OrderLineItem[] = items.map((item) => ({
    menu_item_id: item.menuItemId,
    name: item.name,
    quantity: item.quantity,
    unit_price: calculateLineItemPrice(item),
    modifiers: item.modifiers.map((group) => ({
      group_id: group.groupId,
      group_name: group.groupName,
      selections: group.selections.map((sel) => ({
        id: sel.id,
        name: sel.name,
        price_adjustment: sel.priceAdjustment,
      })),
    })),
    special_instructions: item.specialInstructions,
  }));

  return {
    customer_name: customer.name,
    customer_email: customer.email,
    customer_phone: customer.phone,
    order_type: cartState.orderType,
    scheduled_time: cartState.scheduledTime,
    special_instructions: cartState.specialInstructions,
    items: lineItems,
    subtotal: Math.round(subtotal * 100) / 100,
    tax: Math.round(tax * 100) / 100,
    tip: Math.round(cartState.tip * 100) / 100,
    total: Math.round(total * 100) / 100,
  };
}

/**
 * Validate cart items against current availability
 * Returns list of unavailable item names
 */
export function validateCartAvailability(
  availability: Record<string, boolean>
): string[] {
  const items = cart.get().items;
  const unavailable: string[] = [];

  for (const item of items) {
    if (availability[item.menuItemId.toString()] === false) {
      unavailable.push(item.name);
    }
  }

  return unavailable;
}

/**
 * Format phone number for display/submission
 */
export function formatPhoneNumber(phone: string): string {
  // Remove non-digits
  const digits = phone.replace(/\D/g, "");

  // Format as (XXX) XXX-XXXX
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }

  // With country code
  if (digits.length === 11 && digits[0] === "1") {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }

  return phone;
}

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate phone number format (accepts various formats)
 */
export function isValidPhone(phone: string): boolean {
  const digits = phone.replace(/\D/g, "");
  return digits.length >= 10 && digits.length <= 11;
}
