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
        // DataFlow Analytics - Tech Blue/Purple theme
        client: {
          primary: "#2563eb",           // Blue
          "primary-content": "#ffffff", // White text on blue
          secondary: "#7c3aed",         // Purple
          "secondary-content": "#ffffff", // White text on purple
          accent: "#06b6d4",            // Cyan
          "accent-content": "#ffffff",  // White text on cyan
          neutral: "#0f172a",           // Dark slate
          "neutral-content": "#f8fafc", // Light text on dark
          "base-100": "#ffffff",        // White background
          "base-200": "#f1f5f9",        // Slate-100
          "base-300": "#e2e8f0",        // Slate-200
          "base-content": "#0f172a",    // Dark text
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
