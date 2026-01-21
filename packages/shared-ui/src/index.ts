/**
 * Consult Shared UI
 *
 * HTMX-first Astro components for client sites.
 *
 * Usage:
 *   Copy components from this registry into your site's src/components/
 *   Components are designed to be owned and customized per-site.
 */

// Re-export component paths for documentation purposes
// Actual usage: copy .astro files to your site

export const COMPONENTS = [
  'Header',
  'Footer',
  'ContactForm',
  'ServiceCard',
  'TestimonialBlock',
  'CalEmbed',
  'Button',
  'Container',
] as const;

export const LAYOUTS = ['BaseLayout', 'PageLayout'] as const;

export type ComponentName = (typeof COMPONENTS)[number];
export type LayoutName = (typeof LAYOUTS)[number];
