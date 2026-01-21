# Playbook: New Client Site

Use when scaffolding a new client site from the template.

---

## Prompt

```
Create client site: [NAME]
Slug: [slug]
Industry: [industry]

1. Copy sites/_template/ to sites/[slug]/
2. Configure src/config.ts
3. Set up tailwind.config.ts theme
4. Update wrangler.toml
5. Test locally
6. Deploy
```

---

## Step-by-Step

### 1. Copy Template

```bash
cp -r sites/_template sites/[slug]
cd sites/[slug]
```

### 2. Update config.ts

Edit `src/config.ts`:
- `client.slug` → site slug
- `client.name` → business name
- `client.tagline` → tagline
- `client.phone` → phone number
- `client.email` → email
- `client.address` → address
- `intake.formUrl` → `https://intake.consult.io/[slug]/form`
- `services` → list of services
- `social` → social links
- `nav` → navigation items
- `calcom` → if using Cal.com booking

### 3. Update Theme

Edit `tailwind.config.ts`:
```javascript
daisyui: {
  themes: [{
    client: {
      primary: "[primary color]",
      secondary: "[secondary color]",
      accent: "[accent color]",
      neutral: "[neutral color]",
      "base-100": "[background color]",
    }
  }]
}
```

### 4. Update wrangler.toml

```toml
name = "consult-[slug]"
```

### 5. Update astro.config.mjs

```javascript
site: "https://[slug].consult.io",
```

### 6. Test Locally

```bash
pnpm install
pnpm dev
```

### 7. Deploy

```bash
pnpm deploy
```

---

## Industry Color Palettes

| Industry | Primary | Secondary | Accent | Base |
|----------|---------|-----------|--------|------|
| Coffee shop | #78350f (brown) | #92400e | #fef3c7 (cream) | #fffbeb |
| Junk hauler | #1d4ed8 (blue) | #1e40af | #ea580c (orange) | #ffffff |
| Cleaning | #0369a1 (sky) | #0284c7 | #22c55e (fresh) | #f0f9ff |
| Landscaper | #166534 (green) | #15803d | #a16207 (earth) | #f0fdf4 |
| Barber | #171717 (black) | #262626 | #ca8a04 (gold) | #fafafa |
| SaaS/Tech | #4f46e5 (indigo) | #4338ca | #06b6d4 (cyan) | #ffffff |
| Agency | #7c3aed (violet) | #6d28d9 | #f59e0b (amber) | #faf5ff |

---

## Checklist

- [ ] Template copied
- [ ] config.ts updated
- [ ] Theme colors set
- [ ] wrangler.toml updated
- [ ] astro.config.mjs updated
- [ ] Local dev works
- [ ] Contact form submits
- [ ] Mobile nav works
- [ ] Deployed to Cloudflare
- [ ] Client record created in Django admin

---

## Quick Commands

```bash
# Scaffold (manual)
cp -r sites/_template sites/[slug]

# Scaffold (script, when available)
pnpm new-site

# Dev
cd sites/[slug] && pnpm dev

# Deploy
cd sites/[slug] && pnpm deploy
```
