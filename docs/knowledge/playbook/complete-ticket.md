# Playbook: Complete Ticket / Complete EP

---

## Complete a Ticket

```
Complete ticket [NNN-X].

1. Verify all acceptance criteria are checked in the ticket
2. Set ticket status to "done"
3. Update EP's ticket table (status → done)
4. Add final Progress entry
5. Determine next action:
   - More pending tickets in EP? → Start next one
   - All EP tickets done? → Complete the EP
```

### Final Progress Entry Format

```markdown
### YYYY-MM-DD
- **COMPLETED**
- Delivered: [summary of what was built]
- Tests: [passing/added/n/a]
```

---

## Complete an EP (Sprint)

Use when ALL tickets in the EP are done.

```
Complete EP-[NNN].

1. Verify all tickets show status "done"
2. Set EP status to "complete"
3. Fill in Retrospective section:
   - What went well
   - What could improve
   - Carry-over items (if any)
4. Archive files:
   mv docs/active/enhancement_proposals/EP-[NNN]-*.md docs/archive/enhancement_proposals/
   mv docs/active/tickets/[NNN]-*.md docs/archive/tickets/
5. Update ROADMAP.md:
   - Remove EP from "Active Sprints"
   - Optionally add to "Completed" section
6. Commit: "Complete EP-[NNN]: [title]"
7. Pick next EP from "Planned Sprints" → Activate it
```

---

## Checklist

### Ticket Completion
- [ ] All acceptance criteria checked
- [ ] Status set to "done"
- [ ] EP ticket table updated
- [ ] Final Progress entry added

### EP Completion
- [ ] All tickets done
- [ ] EP status = "complete"
- [ ] Retrospective filled in
- [ ] Files moved to archive/
- [ ] ROADMAP.md updated
- [ ] Changes committed

---

## Example

```
Complete ticket 001-A.

Checking acceptance criteria...
✓ Django deps uncommented
✓ django-environ added
✓ Settings loads from Doppler
✓ migrate succeeds
✓ createsuperuser works
✓ Admin shows all models

All criteria met. Marking 001-A as done.
Updating EP-001 ticket table.

EP-001 status:
- 001-A: done ✓
- 001-B: pending
- 001-C: pending

More tickets remain. Starting 001-B next.
```
