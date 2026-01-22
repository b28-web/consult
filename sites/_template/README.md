# Client Site Template

Astro-based template for Consult client sites using Tailwind CSS v4 and DaisyUI.

## Quick Start

```bash
# Create a new site from this template
pnpm new-site --slug my-client --industry service --register

# Start development server
cd sites/my-client
pnpm dev
```

## Structure

```
src/
├── config.ts           # Site configuration (name, services, etc.)
├── layouts/
│   ├── BaseLayout.astro   # HTML shell with HTMX
│   └── PageLayout.astro   # Nav + content + footer
├── pages/
│   ├── index.astro        # Home page
│   └── contact.astro      # Contact form + Cal.com
├── components/
│   └── CalEmbed.astro     # Cal.com booking widget
└── styles/
    └── global.css         # Tailwind + DaisyUI imports
```

## Configuration

Edit `src/config.ts` to customize:

```typescript
export const config = {
  client: {
    name: "Your Business",
    tagline: "Your tagline here",
    phone: "(555) 123-4567",
    email: "hello@example.com",
    address: "123 Main St, City, ST 12345",
  },
  nav: [
    { label: "Home", href: "/" },
    { label: "Services", href: "/services" },
    { label: "Contact", href: "/contact" },
  ],
  services: [
    { name: "Service One", slug: "service-one", description: "..." },
  ],
  // Optional: Cal.com booking integration
  calcom: {
    username: "your-username",
    eventSlug: "30min",
  },
};
```

## Customization

### Theme Colors

Override DaisyUI theme in `tailwind.config.ts`:

```typescript
daisyui: {
  themes: [{
    client: {
      primary: "#your-primary-color",
      secondary: "#your-secondary-color",
      accent: "#your-accent-color",
      // ... other colors
    },
  }],
},
```

### Fonts

Add custom fonts in `src/styles/global.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=YourFont&display=swap');

:root {
  --font-family-sans: "YourFont", sans-serif;
}
```

### Adding Pages

1. Create a new `.astro` file in `src/pages/`
2. Import and use `PageLayout`
3. Add to `config.nav` if it should appear in navigation

```astro
---
import PageLayout from "@/layouts/PageLayout.astro";
---
<PageLayout title="New Page">
  <section class="py-12 sm:py-16 px-4">
    <!-- Your content -->
  </section>
</PageLayout>
```

## Mobile Responsiveness

The template uses mobile-first responsive design:

- **Breakpoints**: `sm:` (640px), `md:` (768px), `lg:` (1024px)
- **Touch targets**: All buttons meet 44px minimum
- **Hero sections**: Scale appropriately on small screens
- **Navigation**: Hamburger menu on mobile, horizontal on desktop

### Testing Checklist

Test at these viewport widths:
- 320px (small phone)
- 375px (iPhone SE/mini)
- 390px (iPhone 14)
- 768px (tablet)
- 1024px+ (desktop)

## Known Gotchas

### Tailwind v4 + DaisyUI Setup

The `@config` directive in `global.css` is **required** for DaisyUI to work with Tailwind v4:

```css
@config "../../tailwind.config.ts";
@import "tailwindcss";
```

Without this, DaisyUI theme colors won't apply correctly.

### Cal.com Embed

The Cal.com embed loads asynchronously. For best UX:
- Use `mode="inline"` for dedicated booking pages
- Use `mode="popup"` for booking buttons elsewhere

### HTMX Form Handling

Contact forms use HTMX for submission. Ensure your intake worker endpoint returns HTML for `#form-response`.

## Deployment

Sites deploy to Cloudflare Pages via the registry system:

```bash
# Register site for deployment
just register-site my-client

# Deploy to dev environment
just deploy-wizard dev
```

See `sites/registry.yaml` for deployment configuration.
