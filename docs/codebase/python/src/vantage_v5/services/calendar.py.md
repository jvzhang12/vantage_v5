# `src/vantage_v5/services/calendar.py`

Calendar service layer for Vantage V5/V6 experiments. It gives the app a small, typed calendar-day contract before any external calendar MCP, Apple Calendar, or Google Calendar integration exists, and now supports narrow user-scoped local JSON writes for confirmed artifact actions.

## Purpose

- Load calendar events from a local JSON file.
- Resolve simple date phrases such as `today`, `tomorrow`, `yesterday`, and ISO dates against an explicit app/user timezone.
- Return day/week views with sorted events, calendar metadata, free blocks, and compact summaries.
- Support confirmed local user JSON mutations while keeping global/configured calendar files read-only by default.

## Key Classes / Functions

- `CalendarEvent`: normalized calendar event DTO with id, title, start/end datetimes, calendar id/title, all-day flag, location, description, and source.
- `CalendarFreeBlock`: open interval DTO with a derived `duration_minutes`.
- `CalendarDay`: day-level DTO returned by providers and serialized by the API.
- `LocalCalendarProvider`: reads `events.json`, normalizes supported event shapes, filters events by day/range, reports source status, and optionally writes when constructed as user-scoped/writable.
- `current_calendar_date()`: returns today in the configured app/user timezone, defaulting to UTC.
- `resolve_calendar_date()`: maps supported date input into a `date` using either an explicit `today` or the configured timezone.
- `compute_free_blocks()`: clips non-all-day events to the workday, merges overlaps, and returns open blocks.

## Local JSON Shape

The provider accepts either a list of events or an object with `calendars` and `events` keys:

```json
{
  "calendars": [{"id": "school", "title": "School"}],
  "events": [
    {
      "id": "midterm",
      "calendar_id": "school",
      "title": "Midterm study",
      "start": "2026-05-13T14:00:00",
      "end": "2026-05-13T15:30:00",
      "location": "Library"
    }
  ]
}
```

## Notable Behavior

- Defaults the workday window to 09:00-18:00.
- Defaults relative date resolution to UTC unless callers provide a user/app timezone or explicit test date, so calendar/task behavior is independent of the process `TZ`.
- Skips all-day events when computing free blocks, while still returning them as day events.
- Clips events that partially overlap the requested day or workday.
- Merges overlapping busy intervals before calculating free blocks.
- Treats malformed or missing local JSON as an empty calendar rather than failing the app.
- Soft-cancelled events remain in JSON with `status: cancelled` but are hidden from normal reads.
- Write methods preserve unknown event fields where possible.
- Strips timezone info from parsed ISO datetimes for now; this keeps the first backend slice simple, but a real external provider should normalize to the user's timezone before creating these DTOs.
