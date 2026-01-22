# 005-F: Template Hardening

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending
**Priority:** HIGH - blocks remaining site deployments

## Summary

Consolidate fixes and improvements in `sites/_template/` before deploying more sites. Reduces O(n) maintenance burden by fixing issues once in the template rather than across each site.

## Motivation

After deploying 4 sites (coffee-shop, hauler, cleaning, landscaper), we've encountered:
- CSS configuration issues (Tailwind v4 + DaisyUI `@config` directive)
- Mobile responsiveness problems on small screens
- Potential for more issues to emerge

Each fix currently requires updating all existing sites. By hardening the template now, we:
1. Fix issues once, not N times
2. Ensure remaining sites (barber, data-analytics, web-dev, local-agency) deploy correctly
3. Reduce context overhead in future sessions

## Acceptance Criteria

- [ ] Mobile responsiveness audit and fixes
  - [ ] Navbar works on mobile (hamburger menu, proper sizing)
  - [ ] Hero sections scale properly on small screens
  - [ ] Cards stack correctly on mobile
  - [ ] Text remains readable (no overflow, proper sizing)
  - [ ] Buttons are tap-friendly (min 44px touch targets)
- [ ] Template CSS cleanup
  - [ ] `@config` directive in global.css (already done)
  - [ ] Verify DaisyUI theme colors apply correctly
  - [ ] Test dark mode if applicable
- [ ] Template structure review
  - [ ] PageLayout handles all common patterns
  - [ ] Contact form is reusable and styled
  - [ ] Footer renders correctly on all pages
- [ ] Documentation
  - [ ] Update template README with customization guide
  - [ ] Document known gotchas (Tailwind v4 + DaisyUI setup)
- [ ] Propagate fixes to existing sites
  - [ ] coffee-shop
  - [ ] hauler
  - [ ] cleaning
  - [ ] landscaper
- [ ] Verify all 4 deployed sites render correctly on mobile

## Implementation Notes

### Mobile Testing Checklist
Test at these breakpoints:
- 320px (small phone)
- 375px (iPhone SE/mini)
- 390px (iPhone 14)
- 768px (tablet)

### Known Issues to Address
1. Navbar text may overflow on small screens
2. Hero section `min-h-[70vh]` may be too tall on mobile
3. Grid layouts may not collapse properly
4. Button groups may wrap poorly

### Files to Review
```
sites/_template/
├── src/
│   ├── layouts/
│   │   ├── BaseLayout.astro    # HTML shell
│   │   └── PageLayout.astro    # Nav + footer wrapper
│   ├── styles/
│   │   └── global.css          # Tailwind + DaisyUI config
│   └── pages/
│       ├── index.astro         # Home template
│       └── contact.astro       # Contact form
├── tailwind.config.ts          # DaisyUI theme
└── astro.config.mjs            # Vite + Tailwind setup
```

## Progress

(Not started)
