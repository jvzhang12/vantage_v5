# `tests/test_calendar.py`

Unit tests for the local calendar backend seam.

## Coverage

- `resolve_calendar_date()` handles `today`, `tomorrow`, `yesterday`, and ISO `YYYY-MM-DD` dates.
- `LocalCalendarProvider.day()` reads a local JSON calendar file, maps calendar titles, filters only events overlapping the requested day, sorts them chronologically, and serializes source metadata.
- Free-block calculation returns open workday intervals around events.
- Overlapping events are merged before free blocks are emitted.
- All-day events remain visible as events but do not consume focused workday free-block time.
- Writable local providers can create, update, and soft-cancel events.
- Writable updates preserve unknown event fields and cancelled events stay in JSON while disappearing from normal reads.

## Why It Matters

These tests lock in the small provider contract that future MCP or OS-calendar adapters should satisfy. The UI can build a calendar artifact against this day payload now, while the first local write path gives Vantage a safe confirm-before-commit mutation seam.
