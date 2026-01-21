# 005-A: Site Scaffolding Script

**EP:** [EP-005-client-sites](../enhancement_proposals/EP-005-client-sites.md)
**Status:** pending

## Summary

Create a script to scaffold new client sites from the template with interactive prompts.

## Acceptance Criteria

- [ ] `scripts/new-site.sh` or `pnpm new-site` command
- [ ] Prompts for: slug, name, tagline, industry
- [ ] Copies `sites/_template/` to `sites/{slug}/`
- [ ] Updates config.ts with provided values
- [ ] Updates wrangler.toml with project name
- [ ] Sets up reasonable defaults based on industry
- [ ] Prints next steps (customize, deploy)

## Implementation Notes

```bash
#!/bin/bash
# scripts/new-site.sh

read -p "Site slug (lowercase, hyphens): " SLUG
read -p "Business name: " NAME
read -p "Tagline: " TAGLINE
read -p "Industry (coffee-shop/hauler/cleaning/landscaper/barber/saas/agency): " INDUSTRY

# Copy template
cp -r sites/_template sites/$SLUG

# Update config
sed -i "s/slug: \"template\"/slug: \"$SLUG\"/" sites/$SLUG/src/config.ts
sed -i "s/name: \"Business Name\"/name: \"$NAME\"/" sites/$SLUG/src/config.ts
# ... more replacements

# Update wrangler
sed -i "s/name = \"consult-template\"/name = \"consult-$SLUG\"/" sites/$SLUG/wrangler.toml

echo "Site created at sites/$SLUG"
echo "Next steps:"
echo "  1. cd sites/$SLUG"
echo "  2. Edit src/config.ts with full details"
echo "  3. Customize tailwind.config.ts colors"
echo "  4. pnpm dev to preview"
echo "  5. pnpm deploy to ship"
```

Could also be a Node script with better prompts (inquirer):
```typescript
// scripts/new-site.ts
import inquirer from 'inquirer';
import fs from 'fs-extra';
```

## Progress

(Not started)
