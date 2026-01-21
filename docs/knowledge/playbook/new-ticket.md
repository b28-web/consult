# Playbook: Create New Ticket

Use when adding work items. Tickets always belong to an EP.

---

## Add Ticket to Existing EP

```
Add ticket to EP-[NNN]: [brief description]

1. Read docs/active/enhancement_proposals/EP-[NNN]-*.md
2. Find next letter (A, B, C...) in ticket table
3. Create docs/active/tickets/[NNN]-[X]-[slug].md from template
4. Add row to EP's ticket table
5. Update ROADMAP.md if needed
```

---

## Create New EP with Tickets

```
Create new sprint: [goal]

1. Check ROADMAP.md for next EP number (001, 002...)
2. Create docs/active/enhancement_proposals/EP-[NNN]-[slug].md
3. Create tickets: [NNN]-A, [NNN]-B, etc.
4. Add EP to ROADMAP.md under "Planned Sprints"
```

---

## Ticket Template Quick Reference

```markdown
# NNN-X: Title

**EP:** [EP-NNN-slug](../enhancement_proposals/EP-NNN-slug.md)
**Status:** pending

## Summary
One paragraph.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Implementation Notes
Technical details, files to change.

## Progress
(empty until work starts)
```

---

## Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| EP | `EP-NNN-slug` | EP-002-inbox-processing |
| Ticket | `NNN-X-slug` | 002-A-submission-processing |

- **NNN**: Matches EP number (001, 002...)
- **X**: Sequential letter within EP (A, B, C...)
- **slug**: Lowercase, hyphens, descriptive

---

## When to Create New Ticket vs New EP

**New Ticket** (same EP):
- Related to current sprint goal
- Discovered during implementation
- Blocker that needs tracking

**New EP** (new sprint):
- Different goal/theme
- Significant scope
- Different dependencies
