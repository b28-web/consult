# Playbook: Continue Ticket

Use when you know exactly which ticket to resume (mid-session or returning to specific work).

---

## Prompt

```
Continue ticket [NNN-X].

Read:
1. docs/active/tickets/[NNN-X]-*.md
2. docs/active/enhancement_proposals/EP-[NNN]-*.md

Review the Progress section, then continue from where we left off.
Update Progress when done.
```

---

## Checklist

Before coding:
- [ ] Read ticket's acceptance criteria
- [ ] Read ticket's Progress section (last entry)
- [ ] Understand what's already done vs remaining

While coding:
- [ ] Check off acceptance criteria as completed
- [ ] Note any blockers or questions

After coding:
- [ ] Add Progress entry with today's date
- [ ] If all criteria met → mark ticket "done"
- [ ] Update EP's ticket table if status changed

---

## Progress Entry Format

```markdown
### YYYY-MM-DD
- Completed: [what was done]
- Next: [what remains]
- Blockers: [if any, or "none"]
```

---

## Example

```
Continue ticket 001-A.

Reading 001-A-django-bootstrap.md...
- Last progress: "Models stubbed, need to uncomment deps"
- Remaining criteria: migrations, admin, settings

Reading EP-001-backend-foundation.md for context...

Continuing work:
1. Uncommenting Django in pyproject.toml
2. Adding django-environ
3. Updating settings.py...
```
