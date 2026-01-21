# EP-002: Submission Processing & Dashboard Inbox

**Status:** planned
**Last Updated:** 2026-01-21

## Goal

Build the core inbox experience: process raw submissions into classified messages, and render them in a usable dashboard. This is where staff will spend most of their time.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 002-A | Submission processing task | pending |
| 002-B | BAML classification integration | pending |
| 002-C | Dashboard shell with auth | pending |
| 002-D | Inbox list view (HTMX) | pending |
| 002-E | Message detail panel (HTMX) | pending |
| 002-F | Contact profile view | pending |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Task runner | Django management command (cron) | Simple, no Celery overhead yet |
| BAML client | Gemini 2.5 Flash | Fast, cheap for classification |
| Dashboard UI | HTMX partials + DaisyUI | No JS framework, server-rendered |
| Auth | Django sessions | Standard, secure |

## Dependencies

- [x] EP-001 complete (Django running, models migrated)
- [ ] BAML Python client generated (`baml_client/`)
- [ ] Doppler has GOOGLE_API_KEY for Gemini

## Architecture Notes

```
Submission (raw)
     │
     ▼
process_submissions command (polls every 30s)
     │
     ├─→ Find/create Contact (by email or phone)
     │
     ├─→ Create Message record
     │
     ├─→ Call BAML ClassifyMessage()
     │
     └─→ Update Message with classification
           │
           ▼
      Dashboard shows classified message
```

## Progress Log

### 2026-01-21
- EP created
- BAML schemas already exist in baml_src/
- Next: depends on EP-001 completion
