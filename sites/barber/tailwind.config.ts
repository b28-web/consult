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
        // Classic Cuts Barbershop - Black/Gold theme
        client: {
          primary: "#171717",           // Black
          "primary-content": "#fef3c7", // Cream text on black
          secondary: "#d97706",         // Gold
          "secondary-content": "#171717", // Black text on gold
          accent: "#fbbf24",            // Bright gold
          "accent-content": "#171717",  // Black text on accent
          neutral: "#171717",           // Black
          "neutral-content": "#fef3c7", // Cream
          "base-100": "#fef3c7",        // Cream background
          "base-200": "#fde68a",        // Slightly darker cream
          "base-300": "#fcd34d",        // Even darker
          "base-content": "#171717",    // Black text
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
