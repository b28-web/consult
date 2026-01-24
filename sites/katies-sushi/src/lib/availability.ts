/**
 * Availability polling for 86'd items
 *
 * Polls the availability endpoint and updates the DOM.
 * Integrates with cart to block unavailable items.
 */

import { getUnavailableCartItems, removeUnavailableItems } from "./cart";

export interface AvailabilityResponse {
  items: Record<string, boolean>;
  modifiers: Record<string, boolean>;
  as_of: string;
}

// Store current availability for checking before cart actions
let currentAvailability: AvailabilityResponse | null = null;

/**
 * Get current availability data
 */
export function getCurrentAvailability(): AvailabilityResponse | null {
  return currentAvailability;
}

/**
 * Check if a specific item is available
 */
export function isItemAvailable(itemId: number): boolean {
  if (!currentAvailability) return true; // Assume available if no data
  return currentAvailability.items[itemId.toString()] !== false;
}

/**
 * Check if a specific modifier is available
 */
export function isModifierAvailable(modifierId: number): boolean {
  if (!currentAvailability) return true; // Assume available if no data
  return currentAvailability.modifiers[modifierId.toString()] !== false;
}

/**
 * Start polling for availability updates
 *
 * @param slug - Client slug
 * @param onUpdate - Callback when availability changes
 * @param intervalMs - Polling interval (default 60s)
 * @returns Cleanup function to stop polling
 */
export function startAvailabilityPolling(
  slug: string,
  onUpdate: (availability: AvailabilityResponse) => void,
  intervalMs = 60000
): () => void {
  const apiUrl = import.meta.env.PUBLIC_API_URL;

  // Don't poll in development without API
  if (!apiUrl) {
    console.log("[availability] No PUBLIC_API_URL, skipping polling");
    return () => {};
  }

  const url = `${apiUrl}/api/clients/${slug}/availability`;

  const poll = async () => {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data: AvailabilityResponse = await res.json();
        currentAvailability = data;

        // Check for cart items that became unavailable
        const unavailableItems = getUnavailableCartItems(data.items);
        if (unavailableItems.length > 0) {
          // Notify user about unavailable items
          showUnavailableNotification(unavailableItems.map(i => i.name));
        }

        onUpdate(data);
      }
    } catch (err) {
      console.error("[availability] Poll failed:", err);
    }
  };

  // Initial fetch
  poll();

  // Start interval
  const intervalId = setInterval(poll, intervalMs);

  // Return cleanup function
  return () => clearInterval(intervalId);
}

/**
 * Show notification when cart items become unavailable
 */
function showUnavailableNotification(itemNames: string[]): void {
  // Only show in browser
  if (typeof window === "undefined") return;

  const message = itemNames.length === 1
    ? `"${itemNames[0]}" is no longer available and has been removed from your cart.`
    : `${itemNames.length} items are no longer available and have been removed from your cart.`;

  const toast = document.createElement("div");
  toast.className = "toast toast-end toast-top z-50";
  toast.innerHTML = `
    <div class="alert alert-warning">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>${message}</span>
    </div>
  `;
  document.body.appendChild(toast);

  // Remove after 5 seconds
  setTimeout(() => toast.remove(), 5000);
}

/**
 * Update DOM based on availability
 *
 * Adds/removes 'unavailable' class from menu items.
 */
export function updateMenuAvailability(availability: AvailabilityResponse): void {
  // Update items
  Object.entries(availability.items).forEach(([itemId, isAvailable]) => {
    const el = document.querySelector(`[data-item-id="${itemId}"]`);
    if (el) {
      el.classList.toggle("unavailable", !isAvailable);

      // Update badge
      const badge = el.querySelector(".badge-error");
      if (!isAvailable && !badge) {
        const container = el.querySelector(".flex.flex-wrap.items-center");
        if (container) {
          const newBadge = document.createElement("span");
          newBadge.className = "badge badge-error badge-sm";
          newBadge.textContent = "Currently unavailable";
          container.prepend(newBadge);
        }
      } else if (isAvailable && badge) {
        badge.remove();
      }
    }
  });
}
