import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";
import tailwindcss from "@tailwindcss/vite";

// https://astro.build/config
export default defineConfig({
  output: "hybrid", // Static by default, opt-in to SSR per-page
  adapter: cloudflare({
    platformProxy: {
      enabled: true, // Enables env vars in dev
    },
  }),
  vite: {
    plugins: [tailwindcss()],
  },
  // Site-specific: override in actual sites
  site: "https://example.com",
});
