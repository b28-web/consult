# Playbook: Handle Blocked Ticket

Use when you can't continue a ticket due to a blocker.

---

## Prompt

```
Ticket [NNN-X] is blocked.

Blocker: [describe the issue]

Determine resolution path and update tracking.
```

---

## Decision Flow

```
BLOCKED
  │
  ▼
┌─────────────────────────────────┐
│ Can you resolve it quickly?     │
│ (< 30 min, within scope)        │
└─────────────────────────────────┘
  │                 │
  YES               NO
  │                 │
  ▼                 ▼
┌─────────────┐   ┌─────────────────────────────────────┐
│ Resolve it  │   │ Is it a missing dependency/EP?      │
│ Continue    │   └─────────────────────────────────────┘
│ ticket      │     │                 │
└─────────────┘     YES               NO
                    │                 │
                    ▼                 ▼
          ┌─────────────────┐   ┌─────────────────┐
          │ Note dependency │   │ Create ticket   │
          │ Switch to       │   │ for blocker     │
          │ that EP/ticket  │   │ Add to EP       │
          └─────────────────┘   └─────────────────┘
                    │                 │
                    ▼                 ▼
          ┌─────────────────────────────────────┐
          │ Mark current ticket "blocked"       │
          │ Note blocker in Progress            │
          │ Pick different ticket to work on    │
          └─────────────────────────────────────┘
```

---

## Actions

### Quick Resolution
```
1. Fix the issue
2. Continue ticket as normal
3. Note in Progress what was resolved
```

### Create Blocker Ticket
```
1. Create new ticket in same EP (or appropriate EP)
2. Link from blocked ticket's Progress section
3. Set original ticket status to "blocked"
4. Work on blocker ticket (or switch to other work)
```

### Switch EPs (dependency not met)
```
1. Note in current ticket: "Blocked: requires EP-XXX"
2. Note in current EP's Progress Log
3. Check if other EP is ready to work on
4. Either:
   a) Activate and work on the dependency EP
   b) Switch to a different unblocked EP
```

---

## Blocked Ticket Format

Update the ticket:

```markdown
**Status:** blocked

## Progress

### YYYY-MM-DD
- **BLOCKED**: [description of blocker]
- Blocker ticket: [NNN-X] (if created)
- Waiting on: [what needs to happen]
```

---

## Example

```
Ticket 002-B is blocked.
Blocker: BAML client not generated, need baml-cli in environment.

This is a quick fix - adding baml-cli to flox environment.

Resolving...
- Added baml-cli to flox.nix
- Ran flox activate
- Generated client with baml-cli generate
- Blocker resolved, continuing ticket 002-B
```

```
Ticket 003-A is blocked.
Blocker: Need intake worker deployed first (001-B not done).

This is a dependency issue.

Actions:
1. Marking 003-A as blocked
2. Noting in Progress: "Blocked: requires 001-B (intake worker)"
3. Switching to 001-B to resolve dependency
```
