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
        // Custom theme based on site config
        // Override in actual site's tailwind.config.ts
        client: {
          primary: "#4f46e5",
          secondary: "#7c3aed",
          accent: "#06b6d4",
          neutral: "#1f2937",
          "base-100": "#ffffff",
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
