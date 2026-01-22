# EP-002: Submission Processing & Dashboard Inbox

**Status:** complete
**Last Updated:** 2026-01-22

## Goal

Build the core inbox experience: process raw submissions into classified messages, and render them in a usable dashboard. This is where staff will spend most of their time.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| 002-A | Submission processing task | ✓ |
| 002-B | BAML classification integration | ✓ |
| 002-C | Dashboard shell with auth | ✓ |
| 002-D | Inbox list view (HTMX) | ✓ |
| 002-E | Message detail panel (HTMX) | ✓ |
| 002-F | Contact profile view | ✓ |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Task runner | Django management command (cron) | Simple, no Celery overhead yet |
| BAML client | Gemini 2.5 Flash | Fast, cheap for classification |
| Dashboard UI | HTMX partials + DaisyUI | No JS framework, server-rendered |
| Auth | Django sessions | Standard, secure |

## Dependencies

- [x] EP-001 complete (Django running, models migrated)
- [x] BAML Python client generated (`baml_client/`)
- [x] Doppler has GOOGLE_API_KEY for Gemini

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

### 2026-01-22
- 002-F complete: Contact profile view with search, edit, and notes
- Full CRM template structure: list, detail, partials
- Inline editing with HTMX, note creation
- Tests: 17 new tests (63 total)
- **EP-002 COMPLETE** - All 6 tickets done

- 002-E complete: Message detail panel with contact history
- Added contact_history.html partial showing last 5 messages from contact
- Contact name links to CRM profile, "View full profile" link in history
- Tests: 3 new tests (46 total)

- 002-D complete: Inbox list view with HTMX filters and detail panel
- Templates: inbox.html, message_list, message_row, filters, message_detail
- Sorting: urgency (urgent→high→medium→low), then by date
- Tests: 18 new tests (43 total)

- 002-C complete: Dashboard shell with DaisyUI sidebar, login/logout, HTMX
- Tests: 9 dashboard tests

- 002-B complete: BAML classification integrated into process_submissions
- Added Client.vertical field, Message.ai_summary/is_new_lead, Contact.address
- Tests: 16 total (10 base + 6 classification)
- Next: 002-C Dashboard shell with auth

- 002-A complete: `process_submissions` management command implemented
- Tests: 10 passing tests with factory_boy factories
- Next: 002-B BAML classification integration

### 2026-01-21
- EP created
- BAML schemas already exist in baml_src/
- Next: depends on EP-001 completion
