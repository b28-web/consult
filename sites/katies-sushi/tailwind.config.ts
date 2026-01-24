/**
 * Tailwind v4 configuration for restaurant sites.
 *
 * Uses warm, appetizing colors by default.
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
        restaurant: {
          primary: "#b91c1c", // Warm red
          secondary: "#ea580c", // Orange
          accent: "#facc15", // Gold
          neutral: "#292524", // Stone dark
          "base-100": "#fafaf9", // Stone light
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#dc2626",
        },
      },
    ],
  },
} satisfies Config;
