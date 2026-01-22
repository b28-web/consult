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
        // Green Thumb Landscaping theme - natural earth tones
        client: {
          primary: "#166534",
          secondary: "#78350f",
          accent: "#0284c7",
          neutral: "#14532d",
          "base-100": "#f0fdf4",
          "base-content": "#14532d",
          info: "#0284c7",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
