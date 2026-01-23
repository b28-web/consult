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
        // Pixel Perfect Studios: Pink/Purple gradient theme
        client: {
          primary: "#ec4899", // Pink
          secondary: "#8b5cf6", // Purple
          accent: "#06b6d4", // Cyan
          neutral: "#18181b", // Zinc dark
          "base-100": "#fafafa", // Light gray
          "base-content": "#18181b",
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
