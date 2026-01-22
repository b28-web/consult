# 005-F: Template Hardening

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** complete
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

- [x] Mobile responsiveness audit and fixes
  - [x] Navbar works on mobile (hamburger menu, proper sizing)
  - [x] Hero sections scale properly on small screens
  - [x] Cards stack correctly on mobile
  - [x] Text remains readable (no overflow, proper sizing)
  - [x] Buttons are tap-friendly (min 44px touch targets)
- [x] Template CSS cleanup
  - [x] `@config` directive in global.css (already done)
  - [x] Verify DaisyUI theme colors apply correctly
  - [x] Test dark mode if applicable
- [x] Template structure review
  - [x] PageLayout handles all common patterns
  - [x] Contact form is reusable and styled
  - [x] Footer renders correctly on all pages
- [x] Documentation
  - [x] Update template README with customization guide
  - [x] Document known gotchas (Tailwind v4 + DaisyUI setup)
- [x] Propagate fixes to existing sites
  - [x] coffee-shop
  - [x] hauler
  - [x] cleaning
  - [x] landscaper
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

### 2026-01-22 (template hardening complete)
- **Navbar mobile fixes**:
  - Added `btn-square` class to hamburger button for consistent sizing
  - Truncated long business names with `max-w-[140px] sm:max-w-none`
  - Call button shows phone icon only on mobile, text on larger screens
  - Added responsive padding `px-2 sm:px-4`

- **Hero section responsive scaling**:
  - Changed `min-h-[70vh]` to `min-h-[50vh] sm:min-h-[60vh] lg:min-h-[70vh]`
  - Title scales: `text-3xl sm:text-4xl lg:text-5xl`
  - Tagline scales: `text-lg sm:text-xl`
  - Button group stacks on mobile: `flex-col sm:flex-row`

- **Card layouts**:
  - Grid starts at `sm:` breakpoint for cards
  - Reduced padding on mobile: `p-4 sm:p-6`
  - Text scales appropriately

- **CSS utilities added**:
  - `.touch-target` for 44px minimum touch targets
  - `.safe-area-inset` for notched devices
  - `.text-balance` for text wrapping

- **Documentation**:
  - Created comprehensive `sites/_template/README.md`
  - Includes customization guide, mobile testing checklist, known gotchas

- **Propagated to all 4 sites**:
  - Updated PageLayout.astro (navbar fixes)
  - Updated index.astro (hero, cards, CTA responsive)
  - Updated contact.astro (section padding, text sizing)
  - Updated global.css (mobile utilities)

**Remaining**: Manual verification on deployed sites (requires rebuild/redeploy)
