/**
 * Unit tests for cart state management
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  cart,
  cartItemCount,
  cartSubtotal,
  cartTax,
  cartTotal,
  calculateItemPrice,
  addToCart,
  updateQuantity,
  incrementQuantity,
  decrementQuantity,
  removeFromCart,
  updateItemInstructions,
  clearCart,
  setOrderType,
  setScheduledTime,
  setTip,
  setTipPercentage,
  setOrderInstructions,
  canAddToCart,
  getUnavailableCartItems,
  removeUnavailableItems,
  isCartEmpty,
  getCartItem,
  formatPrice,
  ESTIMATED_TAX_RATE,
  type CartItem,
} from "./cart";

describe("Cart State Management", () => {
  beforeEach(() => {
    clearCart();
  });

  describe("Initial State", () => {
    it("should start with empty cart", () => {
      expect(cart.get().items).toEqual([]);
      expect(isCartEmpty()).toBe(true);
    });

    it("should have default order type as pickup", () => {
      expect(cart.get().orderType).toBe("pickup");
    });

    it("should have zero tip by default", () => {
      expect(cart.get().tip).toBe(0);
    });
  });

  describe("addToCart", () => {
    it("should add item to cart", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const items = cart.get().items;
      expect(items).toHaveLength(1);
      expect(items[0].name).toBe("Burger");
      expect(items[0].basePrice).toBe(12.99);
    });

    it("should generate unique ID for each item", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const items = cart.get().items;
      expect(items).toHaveLength(2);
      expect(items[0].id).not.toBe(items[1].id);
    });

    it("should allow same item with different modifiers", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [
          {
            groupId: 1,
            groupName: "Cheese",
            selections: [{ id: 1, name: "Cheddar", priceAdjustment: 1.0 }],
          },
        ],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [
          {
            groupId: 1,
            groupName: "Cheese",
            selections: [{ id: 2, name: "Swiss", priceAdjustment: 1.5 }],
          },
        ],
        specialInstructions: "",
      });

      expect(cart.get().items).toHaveLength(2);
    });
  });

  describe("updateQuantity", () => {
    it("should update item quantity", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      updateQuantity(itemId, 3);

      expect(cart.get().items[0].quantity).toBe(3);
    });

    it("should remove item when quantity is zero", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      updateQuantity(itemId, 0);

      expect(cart.get().items).toHaveLength(0);
    });

    it("should remove item when quantity is negative", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      updateQuantity(itemId, -1);

      expect(cart.get().items).toHaveLength(0);
    });
  });

  describe("incrementQuantity / decrementQuantity", () => {
    it("should increment quantity by 1", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      incrementQuantity(itemId);

      expect(cart.get().items[0].quantity).toBe(2);
    });

    it("should decrement quantity by 1", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 3,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      decrementQuantity(itemId);

      expect(cart.get().items[0].quantity).toBe(2);
    });

    it("should remove item when decrementing from 1", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      decrementQuantity(itemId);

      expect(cart.get().items).toHaveLength(0);
    });
  });

  describe("removeFromCart", () => {
    it("should remove item by ID", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 2,
        name: "Fries",
        basePrice: 4.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const burgerId = cart.get().items[0].id;
      removeFromCart(burgerId);

      const items = cart.get().items;
      expect(items).toHaveLength(1);
      expect(items[0].name).toBe("Fries");
    });
  });

  describe("updateItemInstructions", () => {
    it("should update special instructions for item", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      updateItemInstructions(itemId, "No onions please");

      expect(cart.get().items[0].specialInstructions).toBe("No onions please");
    });
  });

  describe("clearCart", () => {
    it("should remove all items and reset state", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      setTip(5);
      setOrderType("delivery");

      clearCart();

      expect(cart.get().items).toHaveLength(0);
      expect(cart.get().tip).toBe(0);
      expect(cart.get().orderType).toBe("pickup");
    });
  });

  describe("calculateItemPrice", () => {
    it("should calculate price without modifiers", () => {
      const item: CartItem = {
        id: "test",
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 2,
        modifiers: [],
        specialInstructions: "",
      };

      expect(calculateItemPrice(item)).toBeCloseTo(25.98, 2);
    });

    it("should include modifier prices", () => {
      const item: CartItem = {
        id: "test",
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [
          {
            groupId: 1,
            groupName: "Cheese",
            selections: [
              { id: 1, name: "Cheddar", priceAdjustment: 1.0 },
              { id: 2, name: "Extra Bacon", priceAdjustment: 2.5 },
            ],
          },
        ],
        specialInstructions: "",
      };

      expect(calculateItemPrice(item)).toBeCloseTo(16.49, 2);
    });

    it("should multiply by quantity", () => {
      const item: CartItem = {
        id: "test",
        menuItemId: 1,
        name: "Burger",
        basePrice: 10.0,
        quantity: 3,
        modifiers: [
          {
            groupId: 1,
            groupName: "Cheese",
            selections: [{ id: 1, name: "Cheddar", priceAdjustment: 2.0 }],
          },
        ],
        specialInstructions: "",
      };

      expect(calculateItemPrice(item)).toBeCloseTo(36.0, 2);
    });
  });

  describe("Computed Values", () => {
    it("should calculate cart item count", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 2,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 2,
        name: "Fries",
        basePrice: 4.99,
        quantity: 3,
        modifiers: [],
        specialInstructions: "",
      });

      expect(cartItemCount.get()).toBe(5);
    });

    it("should calculate subtotal", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 10.0,
        quantity: 2,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 2,
        name: "Fries",
        basePrice: 5.0,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      expect(cartSubtotal.get()).toBeCloseTo(25.0, 2);
    });

    it("should calculate tax", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 100.0,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      expect(cartTax.get()).toBeCloseTo(100 * ESTIMATED_TAX_RATE, 2);
    });

    it("should calculate total with tip", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 100.0,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      setTip(15);

      const expectedTotal = 100 + 100 * ESTIMATED_TAX_RATE + 15;
      expect(cartTotal.get()).toBeCloseTo(expectedTotal, 2);
    });
  });

  describe("Order Settings", () => {
    it("should set order type", () => {
      setOrderType("delivery");
      expect(cart.get().orderType).toBe("delivery");
    });

    it("should set scheduled time", () => {
      const time = "2026-01-24T12:00:00Z";
      setScheduledTime(time);
      expect(cart.get().scheduledTime).toBe(time);
    });

    it("should clear scheduled time with null", () => {
      setScheduledTime("2026-01-24T12:00:00Z");
      setScheduledTime(null);
      expect(cart.get().scheduledTime).toBeNull();
    });

    it("should set tip amount", () => {
      setTip(10);
      expect(cart.get().tip).toBe(10);
    });

    it("should not allow negative tip", () => {
      setTip(-5);
      expect(cart.get().tip).toBe(0);
    });

    it("should set tip percentage", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 100.0,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      setTipPercentage(20);

      expect(cart.get().tip).toBeCloseTo(20, 2);
    });

    it("should set order instructions", () => {
      setOrderInstructions("Leave at door");
      expect(cart.get().specialInstructions).toBe("Leave at door");
    });
  });

  describe("Availability Checking", () => {
    it("should return true when item is available", () => {
      const availability = { "1": true, "2": true };
      expect(canAddToCart(1, availability)).toBe(true);
    });

    it("should return false when item is unavailable", () => {
      const availability = { "1": false, "2": true };
      expect(canAddToCart(1, availability)).toBe(false);
    });

    it("should return true when item not in availability map", () => {
      const availability = { "2": true };
      expect(canAddToCart(1, availability)).toBe(true);
    });

    it("should find unavailable cart items", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 2,
        name: "Fries",
        basePrice: 4.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const availability = { "1": false, "2": true };
      const unavailable = getUnavailableCartItems(availability);

      expect(unavailable).toHaveLength(1);
      expect(unavailable[0].name).toBe("Burger");
    });

    it("should remove unavailable items", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      addToCart({
        menuItemId: 2,
        name: "Fries",
        basePrice: 4.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const availability = { "1": false, "2": true };
      const removed = removeUnavailableItems(availability);

      expect(removed).toHaveLength(1);
      expect(removed[0].name).toBe("Burger");
      expect(cart.get().items).toHaveLength(1);
      expect(cart.get().items[0].name).toBe("Fries");
    });
  });

  describe("Utility Functions", () => {
    it("should check if cart is empty", () => {
      expect(isCartEmpty()).toBe(true);

      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      expect(isCartEmpty()).toBe(false);
    });

    it("should get cart item by ID", () => {
      addToCart({
        menuItemId: 1,
        name: "Burger",
        basePrice: 12.99,
        quantity: 1,
        modifiers: [],
        specialInstructions: "",
      });

      const itemId = cart.get().items[0].id;
      const item = getCartItem(itemId);

      expect(item).toBeDefined();
      expect(item?.name).toBe("Burger");
    });

    it("should return undefined for non-existent item", () => {
      expect(getCartItem("non-existent")).toBeUndefined();
    });

    it("should format price correctly", () => {
      expect(formatPrice(12.5)).toBe("$12.50");
      expect(formatPrice(0)).toBe("$0.00");
      expect(formatPrice(100)).toBe("$100.00");
    });
  });
});
