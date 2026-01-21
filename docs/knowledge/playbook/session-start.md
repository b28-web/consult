# Playbook: Session Bootstrap

**This is the main entry point for coding sessions.**

Copy this prompt to start work. It will guide you through determining what to do next.

---

## Prompt

```
Bootstrap coding session.

Read these files in order:
1. docs/active/ROADMAP.md (current state, priorities)
2. Any EP marked "active" in enhancement_proposals/
3. Any ticket marked "in-progress" in tickets/

Then follow the decision flow below to determine next action.
```

---

## Decision Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ Is there a ticket marked            │
│ "in-progress"?                      │
└─────────────────────────────────────┘
  │                 │
  YES               NO
  │                 │
  ▼                 ▼
┌─────────────┐   ┌─────────────────────────────────────┐
│ RESUME      │   │ Is there an EP marked "active"?     │
│ Continue    │   └─────────────────────────────────────┘
│ that ticket │     │                 │
└─────────────┘     YES               NO
                    │                 │
                    ▼                 ▼
          ┌─────────────────┐   ┌─────────────────┐
          │ Pick next       │   │ ACTIVATE        │
          │ "pending"       │   │ Pick first EP   │
          │ ticket in EP    │   │ from "Planned"  │
          │ → START TICKET  │   │ in ROADMAP      │
          └─────────────────┘   └─────────────────┘
                    │                 │
                    ▼                 ▼
          ┌─────────────────┐   ┌─────────────────┐
          │ All tickets in  │   │ Set EP status   │
          │ EP done?        │   │ to "active"     │
          └─────────────────┘   │ → Pick first    │
            │           │       │   ticket        │
            YES         NO      └─────────────────┘
            │           │
            ▼           ▼
     ┌────────────┐  ┌─────────────┐
     │ COMPLETE   │  │ START       │
     │ Archive EP │  │ TICKET      │
     │ → Pick     │  └─────────────┘
     │ next EP    │
     └────────────┘
```

---

## Actions

### RESUME (in-progress ticket exists)

```
Read:
1. docs/active/tickets/{ticket}.md
2. docs/active/enhancement_proposals/{EP}.md

Look at:
- Acceptance criteria (what's left?)
- Progress section (where did we leave off?)

Continue work. Update Progress section when done for the day.
```

### START TICKET (beginning new ticket)

```
Read:
1. docs/active/tickets/{ticket}.md
2. docs/active/enhancement_proposals/{EP}.md (for context)

Do:
1. Set ticket status to "in-progress"
2. Update EP's ticket table (status → in-progress)
3. Begin implementation
4. Check off acceptance criteria as completed
5. Add Progress entry with today's work

When all criteria met:
→ Use "Complete Ticket" flow
```

### COMPLETE TICKET

```
1. Verify all acceptance criteria checked
2. Set ticket status to "done"
3. Update EP's ticket table (status → done)
4. Add final Progress entry

If more tickets remain in EP:
→ Pick next pending ticket

If all tickets in EP are done:
→ Use "Complete EP" flow
```

### COMPLETE EP (all tickets done)

```
1. Set EP status to "complete"
2. Fill in Retrospective section
3. Move files to archive:
   mv docs/active/enhancement_proposals/EP-NNN-*.md docs/archive/enhancement_proposals/
   mv docs/active/tickets/NNN-*.md docs/archive/tickets/
4. Update ROADMAP.md (move to completed or remove)
5. Pick next EP from "Planned Sprints"
```

### ACTIVATE EP (starting new sprint)

```
1. Read the EP file thoroughly
2. Set EP status to "active"
3. Move EP from "Planned" to "Active" in ROADMAP.md
4. Check dependencies - are they met?
   - If NO: note blocker, pick different EP or resolve
   - If YES: pick first ticket (usually NNN-A)
5. → START TICKET
```

---

## Handling Blockers

If you encounter a blocker:

```
1. Note the blocker in ticket's Progress section
2. Set ticket status to "blocked"
3. Options:
   a) Resolve the blocker if quick
   b) Create a new ticket for the blocker
   c) Switch to another ticket in the same EP
   d) If EP is fully blocked, note in EP and switch EPs
```

---

## Quick Reference

| Want to... | Read... |
|------------|---------|
| See priorities | `docs/active/ROADMAP.md` |
| Understand current sprint | `docs/active/enhancement_proposals/EP-NNN-*.md` |
| See ticket details | `docs/active/tickets/NNN-X-*.md` |
| Learn how something works | `docs/knowledge/patterns/*.md` |
| Find a workflow prompt | `docs/knowledge/playbook/*.md` |

---

## Example Session

```
> Bootstrap coding session.

Reading ROADMAP.md...
- Active: EP-001 Backend Foundation
- 001-A (in-progress), 001-B (pending), 001-C (pending)

Reading EP-001-backend-foundation.md...
- Goal: Get full stack working end-to-end
- Dependencies: All met

Reading 001-A-django-bootstrap.md...
- Status: in-progress
- Progress: "Models stubbed, need to uncomment deps"

Decision: RESUME ticket 001-A

Continuing from last session:
- Uncommenting Django deps in pyproject.toml
- Adding django-environ
- Running migrations...
```
