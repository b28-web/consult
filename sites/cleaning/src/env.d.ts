/// <reference types="astro/client" />

type Runtime = import("@astrojs/cloudflare").Runtime<Env>;

interface Env {
  // Secrets from Doppler
  INTAKE_API_KEY?: string;
  // Add other env vars as needed
}

declare namespace App {
  interface Locals extends Runtime {}
}
