/**
 * Tailwind v4 configuration for client sites.
 *
 * Uses CSS-first @theme config via the shared preset.
 * Site-specific overrides go in src/styles/theme.css
 */
import type { Config } from "tailwindcss";
import daisyui from "daisyui";

export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}"],
  plugins: [daisyui],
  daisyui: {
    themes: [
      {
        // The Daily Grind - warm brown/cream coffee theme
        client: {
          primary: "#78350f", // Rich brown
          "primary-content": "#fef3c7", // Cream text on brown
          secondary: "#92400e", // Amber brown
          "secondary-content": "#fef3c7",
          accent: "#b45309", // Warm amber
          "accent-content": "#ffffff",
          neutral: "#44403c", // Stone
          "neutral-content": "#fafaf9",
          "base-100": "#fef3c7", // Cream background
          "base-200": "#fde68a", // Darker cream
          "base-300": "#fcd34d", // Even darker
          "base-content": "#78350f", // Brown text
          info: "#0891b2",
          success: "#16a34a",
          warning: "#d97706",
          error: "#dc2626",
        },
      },
    ],
  },
} satisfies Config;
