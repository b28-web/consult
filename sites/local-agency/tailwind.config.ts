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
        // Consult Local: Professional blue/slate theme
        client: {
          primary: "#1e40af", // Blue
          secondary: "#475569", // Slate
          accent: "#0ea5e9", // Sky blue
          neutral: "#1e293b", // Dark slate
          "base-100": "#ffffff",
          "base-content": "#1e293b",
          info: "#3b82f6",
          success: "#22c55e",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
    ],
  },
} satisfies Config;
