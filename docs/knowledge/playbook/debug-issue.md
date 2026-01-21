# Playbook: Debug Issue

Use when something isn't working as expected.

---

## Prompt

```
Debug: [brief description]

Symptoms:
- [what you observed]

Expected:
- [what should happen]

Context:
- [what you were doing]
- [any error messages]

Please investigate, explain the root cause, and propose a fix.
Do not make changes until I confirm.
```

---

## Investigation Flow

```
ISSUE REPORTED
  │
  ▼
┌─────────────────────────────────┐
│ 1. Reproduce the issue          │
│    - Can you trigger it?        │
│    - What are exact steps?      │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 2. Identify the layer           │
│    - Site? Worker? Django? DB?  │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 3. Check logs/errors            │
│    - Browser console            │
│    - Worker logs (wrangler tail)│
│    - Django logs                │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 4. Find root cause              │
│    - Trace the data flow        │
│    - Check configs/env vars     │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 5. Propose fix                  │
│    - Explain what and why       │
│    - Wait for confirmation      │
└─────────────────────────────────┘
```

---

## Common Issues by Layer

### Site Issues

| Symptom | Check |
|---------|-------|
| Page 404 | File exists in `src/pages/`? |
| Styles broken | Tailwind config correct? pnpm build works? |
| Form not submitting | Action URL correct? CORS? |
| HTMX not working | Script loaded? hx-* attributes correct? |

```bash
# Rebuild
cd sites/[slug] && pnpm build

# Check build errors
pnpm build 2>&1 | head -50
```

### Worker Issues

| Symptom | Check |
|---------|-------|
| 404 response | Route pattern matches? Deployed? |
| 500 error | Check wrangler tail logs |
| CORS error | Headers set in response? |
| DB write fails | NEON_DATABASE_URL set? |

```bash
# View live logs
cd workers/intake && wrangler tail

# Check deployment
wrangler deployments list
```

### Django Issues

| Symptom | Check |
|---------|-------|
| Import error | Dependencies installed? venv active? |
| Migration error | Models valid? DB connected? |
| 403 Forbidden | CSRF? Auth? Middleware? |
| Tenant data leak | Using for_client()? |

```bash
# Check Django
doppler run -- uv run python apps/web/manage.py check

# Run migrations
doppler run -- uv run python apps/web/manage.py migrate

# Shell for debugging
doppler run -- uv run python apps/web/manage.py shell
```

### Environment Issues

| Symptom | Check |
|---------|-------|
| "Command not found" | flox activate? |
| "Secret not found" | doppler configured? |
| Wrong environment | doppler setup? |

```bash
# Check Doppler
doppler secrets

# Check flox
flox list
```

---

## After Fixing

If the fix reveals a pattern:
1. Update `docs/knowledge/patterns/` if it's a "how things work" insight
2. Create a ticket if it needs more work
3. Add to this debug playbook if it's a common issue

---

## Example

```
Debug: Contact form returns 500 error

Symptoms:
- Fill out form on coffee-shop site
- Click submit, spinner shows
- Browser shows "Failed to fetch"

Expected:
- Form submits, success message appears

Context:
- Just deployed the site
- Worker is deployed

Investigating...

1. Checking browser Network tab:
   - POST to /intake/coffee-shop/form returns 500

2. Checking worker logs (wrangler tail):
   - "ReferenceError: sql is not defined"

3. Root cause:
   - writeSubmission() has TODO comment, not implemented
   - @neondatabase/serverless not added to worker

Fix:
1. Add @neondatabase/serverless to workers/intake/package.json
2. Implement writeSubmission() with actual SQL

Want me to proceed with this fix?
```
