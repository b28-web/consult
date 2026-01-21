# 001-A: Django Backend Bootstrap

**EP:** [EP-001-backend-foundation](../enhancement_proposals/EP-001-backend-foundation.md)
**Status:** completed

## Summary

Set up the Django backend with core models, migrations, and basic admin. Make it runnable with `doppler run -- uv run python manage.py runserver`.

## Acceptance Criteria

- [x] Django dependencies uncommented in pyproject.toml
- [x] django-environ added for DATABASE_URL parsing
- [x] Settings properly loads from Doppler (via environment variables)
- [x] `manage.py migrate` succeeds
- [x] `manage.py createsuperuser` works (tested locally)
- [x] Admin shows all models (9 models registered)

## Implementation Notes

```
pyproject.toml                    # Uncomment Django deps, add django-environ
apps/web/config/settings.py       # Use environ for DATABASE_URL, SECRET_KEY
apps/web/core/admin.py            # Register Client, User
apps/web/inbox/admin.py           # Register Contact, Message, Submission
apps/web/crm/admin.py             # Register Tag, Job, Note
```

## Progress

### 2026-01-21
- Models stubbed in all apps
- Settings file exists but needs environ integration
- Next: uncomment deps and wire up settings

### 2026-01-21 (session 2)
- Uncommented Django dependencies in pyproject.toml
- Integrated django-environ for SECRET_KEY, DATABASE_URL, DEBUG, ALLOWED_HOSTS
- Fixed settings module paths (apps.web.config.settings)
- Created admin.py files for all apps with proper registrations
- Fixed Django 6.0 API changes (CheckConstraint.condition, non-subscriptable ModelAdmin)
- Fixed model field conflict (Contact.notes → Contact.internal_notes)
- Created initial migrations for core, inbox, crm apps
- All ruff and mypy checks pass
- Migrations tested successfully with SQLite
- **Status: COMPLETED** - Ready for Doppler configuration
