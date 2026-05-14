from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
import json
from pathlib import Path
from typing import Any


DEFAULT_WORKDAY_START = time(9, 0)
DEFAULT_WORKDAY_END = time(18, 0)


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    calendar_id: str = "local"
    calendar_title: str = "Calendar"
    all_day: bool = False
    location: str = ""
    description: str = ""
    source: str = "local_calendar"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "calendar_id": self.calendar_id,
            "calendar_title": self.calendar_title,
            "all_day": self.all_day,
            "location": self.location,
            "description": self.description,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class CalendarFreeBlock:
    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        return max(0, int((self.end - self.start).total_seconds() // 60))

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
        }


@dataclass(frozen=True, slots=True)
class CalendarDay:
    date: date
    events: tuple[CalendarEvent, ...]
    free_blocks: tuple[CalendarFreeBlock, ...]
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        busy_minutes = sum(block.duration_minutes for block in _busy_blocks_for_day(self.events, self.date))
        free_minutes = sum(block.duration_minutes for block in self.free_blocks)
        return {
            "date": self.date.isoformat(),
            "source": dict(self.source),
            "events": [event.to_dict() for event in self.events],
            "free_blocks": [block.to_dict() for block in self.free_blocks],
            "summary": {
                "event_count": len(self.events),
                "free_block_count": len(self.free_blocks),
                "busy_minutes": busy_minutes,
                "free_minutes": free_minutes,
                "workday_start": DEFAULT_WORKDAY_START.strftime("%H:%M"),
                "workday_end": DEFAULT_WORKDAY_END.strftime("%H:%M"),
            },
        }


@dataclass(frozen=True, slots=True)
class CalendarWeek:
    start_date: date
    end_date: date
    days: tuple[CalendarDay, ...]
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        serialized_days = [day.to_dict() for day in self.days]
        event_count = sum(int(day["summary"]["event_count"]) for day in serialized_days)
        free_block_count = sum(int(day["summary"]["free_block_count"]) for day in serialized_days)
        busy_minutes = sum(int(day["summary"]["busy_minutes"]) for day in serialized_days)
        free_minutes = sum(int(day["summary"]["free_minutes"]) for day in serialized_days)
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days": serialized_days,
            "source": dict(self.source),
            "summary": {
                "day_count": len(serialized_days),
                "event_count": event_count,
                "free_block_count": free_block_count,
                "busy_minutes": busy_minutes,
                "free_minutes": free_minutes,
                "workday_start": DEFAULT_WORKDAY_START.strftime("%H:%M"),
                "workday_end": DEFAULT_WORKDAY_END.strftime("%H:%M"),
            },
        }


class LocalCalendarProvider:
    def __init__(self, *, events_path: Path | None, writable: bool = False) -> None:
        self.events_path = events_path
        self.writable = writable

    def day(self, target_date: date) -> CalendarDay:
        events = tuple(self.list_events(start=_day_start(target_date), end=_day_end(target_date)))
        return CalendarDay(
            date=target_date,
            events=events,
            free_blocks=tuple(compute_free_blocks(target_date=target_date, events=events)),
            source=self.source_status(event_count=len(events)),
        )

    def week(self, target_date: date) -> CalendarWeek:
        start_date = week_start_for(target_date)
        days = tuple(self.day(start_date + timedelta(days=offset)) for offset in range(7))
        event_count = sum(len(day.events) for day in days)
        return CalendarWeek(
            start_date=start_date,
            end_date=start_date + timedelta(days=6),
            days=days,
            source=self.source_status(event_count=event_count),
        )

    def list_events(self, *, start: datetime, end: datetime) -> list[CalendarEvent]:
        events = [
            event
            for event in self._read_events()
            if event.start < end and event.end > start
        ]
        return sorted(events, key=lambda event: (event.start, event.end, event.title.lower()))

    def source_status(self, *, event_count: int | None = None) -> dict[str, Any]:
        configured = bool(self.events_path and self.events_path.exists())
        writable = bool(self.writable and self.events_path)
        status = {
            "kind": "local_json",
            "label": "Local calendar",
            "configured": configured,
            "read_only": not writable,
            "event_count": event_count,
        }
        if writable:
            status["writable"] = True
        return status

    def create_event(
        self,
        *,
        title: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "local",
        location: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        self._ensure_writable()
        payload = self._read_payload()
        events = _raw_event_records(payload)
        raw_event = {
            "id": _next_event_id(events, title=title),
            "calendar_id": calendar_id or "local",
            "title": title.strip() or "Untitled event",
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        if location:
            raw_event["location"] = location
        if description:
            raw_event["description"] = description
        events.append(raw_event)
        self._write_payload(payload)
        return {
            "before": None,
            "after": raw_event,
            "event_id": raw_event["id"],
            "summary": f"Created calendar event '{raw_event['title']}'.",
        }

    def update_event(self, event_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        self._ensure_writable()
        payload = self._read_payload()
        event = _find_raw_event(payload, event_id)
        before = dict(event)
        for key in ["title", "start", "end", "calendar_id", "location", "description", "all_day"]:
            if key in updates:
                event[key] = updates[key]
        self._write_payload(payload)
        before_title = _text(before.get("title") or event_id)
        after_title = _text(event.get("title") or event_id)
        if before_title != after_title:
            summary = f"Updated calendar event '{before_title}' to '{after_title}'."
        else:
            summary = f"Updated calendar event '{after_title}'."
        return {
            "before": before,
            "after": dict(event),
            "event_id": event_id,
            "summary": summary,
        }

    def soft_cancel_event(self, event_id: str) -> dict[str, Any]:
        self._ensure_writable()
        payload = self._read_payload()
        event = _find_raw_event(payload, event_id)
        before = dict(event)
        event["status"] = "cancelled"
        self._write_payload(payload)
        return {
            "before": before,
            "after": dict(event),
            "event_id": event_id,
            "summary": f"Canceled calendar event '{before.get('title') or event_id}'.",
        }

    def _read_events(self) -> list[CalendarEvent]:
        if not self.events_path or not self.events_path.exists():
            return []
        try:
            payload = json.loads(self.events_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        calendars = _calendar_titles(payload)
        raw_events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(raw_events, list):
            return []
        events: list[CalendarEvent] = []
        for index, raw_event in enumerate(raw_events):
            if _is_cancelled(raw_event):
                continue
            event = _parse_event(raw_event, calendars=calendars, fallback_index=index)
            if event is not None:
                events.append(event)
        return events

    def _ensure_writable(self) -> None:
        if not self.writable or not self.events_path:
            raise PermissionError("Calendar source is read-only.")

    def _read_payload(self) -> dict[str, Any]:
        if not self.events_path or not self.events_path.exists():
            return {"calendars": [{"id": "local", "title": "Calendar"}], "events": []}
        try:
            payload = json.loads(self.events_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Calendar events file is not valid JSON.") from exc
        if isinstance(payload, list):
            return {"calendars": [{"id": "local", "title": "Calendar"}], "events": payload}
        if not isinstance(payload, dict):
            raise ValueError("Calendar events file must contain a JSON object or list.")
        if not isinstance(payload.get("events"), list):
            payload["events"] = []
        if not isinstance(payload.get("calendars"), list):
            payload["calendars"] = [{"id": "local", "title": "Calendar"}]
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self._ensure_writable()
        assert self.events_path is not None
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.events_path.with_suffix(f"{self.events_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.events_path)


def resolve_calendar_date(value: str | None, *, today: date | None = None) -> date:
    base = today or date.today()
    normalized = str(value or "today").strip().lower()
    if normalized in {"", "today"}:
        return base
    if normalized == "tomorrow":
        return base + timedelta(days=1)
    if normalized == "yesterday":
        return base - timedelta(days=1)
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("date must be today, tomorrow, yesterday, or YYYY-MM-DD") from exc


def week_start_for(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def compute_free_blocks(
    *,
    target_date: date,
    events: tuple[CalendarEvent, ...] | list[CalendarEvent],
    workday_start: time = DEFAULT_WORKDAY_START,
    workday_end: time = DEFAULT_WORKDAY_END,
) -> list[CalendarFreeBlock]:
    window_start = datetime.combine(target_date, workday_start)
    window_end = datetime.combine(target_date, workday_end)
    if window_end <= window_start:
        return []
    busy_blocks = _busy_blocks_for_day(events, target_date, workday_start=workday_start, workday_end=workday_end)
    free_blocks: list[CalendarFreeBlock] = []
    cursor = window_start
    for block in busy_blocks:
        if cursor < block.start:
            free_blocks.append(CalendarFreeBlock(start=cursor, end=block.start))
        cursor = max(cursor, block.end)
    if cursor < window_end:
        free_blocks.append(CalendarFreeBlock(start=cursor, end=window_end))
    return [block for block in free_blocks if block.duration_minutes > 0]


def _busy_blocks_for_day(
    events: tuple[CalendarEvent, ...] | list[CalendarEvent],
    target_date: date,
    *,
    workday_start: time = DEFAULT_WORKDAY_START,
    workday_end: time = DEFAULT_WORKDAY_END,
) -> list[CalendarFreeBlock]:
    window_start = datetime.combine(target_date, workday_start)
    window_end = datetime.combine(target_date, workday_end)
    raw_blocks: list[CalendarFreeBlock] = []
    for event in events:
        if event.all_day:
            continue
        start = max(event.start, window_start)
        end = min(event.end, window_end)
        if start < end:
            raw_blocks.append(CalendarFreeBlock(start=start, end=end))
    raw_blocks.sort(key=lambda block: (block.start, block.end))
    merged: list[CalendarFreeBlock] = []
    for block in raw_blocks:
        if not merged or block.start > merged[-1].end:
            merged.append(block)
            continue
        previous = merged[-1]
        merged[-1] = CalendarFreeBlock(start=previous.start, end=max(previous.end, block.end))
    return merged


def _parse_event(raw_event: Any, *, calendars: dict[str, str], fallback_index: int) -> CalendarEvent | None:
    if not isinstance(raw_event, dict):
        return None
    all_day = bool(raw_event.get("all_day") or raw_event.get("allDay"))
    start = _parse_datetime(raw_event.get("start"), all_day=all_day)
    if start is None:
        return None
    end = _parse_datetime(raw_event.get("end"), all_day=all_day)
    if end is None:
        end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    if end <= start:
        end = start + (timedelta(days=1) if all_day else timedelta(minutes=30))
    calendar_id = _text(raw_event.get("calendar_id") or raw_event.get("calendarId") or "local")
    return CalendarEvent(
        id=_text(raw_event.get("id") or f"local-event-{fallback_index + 1}"),
        title=_text(raw_event.get("title") or raw_event.get("summary") or "Untitled event"),
        start=start,
        end=end,
        calendar_id=calendar_id,
        calendar_title=calendars.get(calendar_id, calendar_id),
        all_day=all_day,
        location=_text(raw_event.get("location")),
        description=_text(raw_event.get("description")),
    )


def _raw_event_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_events = payload.setdefault("events", [])
    if not isinstance(raw_events, list):
        raw_events = []
        payload["events"] = raw_events
    return raw_events


def _find_raw_event(payload: dict[str, Any], event_id: str) -> dict[str, Any]:
    target_id = _text(event_id)
    if not target_id:
        raise ValueError("Calendar event id is required.")
    for event in _raw_event_records(payload):
        if not isinstance(event, dict):
            continue
        if _raw_event_id(event) == target_id:
            return event
    raise FileNotFoundError(f"Calendar event '{target_id}' was not found.")


def _raw_event_id(raw_event: dict[str, Any]) -> str:
    return _text(raw_event.get("id") or raw_event.get("event_id") or raw_event.get("eventId"))


def _is_cancelled(raw_event: Any) -> bool:
    if not isinstance(raw_event, dict):
        return False
    status = _text(raw_event.get("status") or raw_event.get("state")).lower()
    return status in {"cancelled", "canceled", "deleted", "removed"}


def _next_event_id(events: list[dict[str, Any]], *, title: str) -> str:
    base = _slug(title) or "calendar-event"
    used_ids = {_raw_event_id(event) for event in events if isinstance(event, dict)}
    if base not in used_ids:
        return base
    index = 2
    while f"{base}-{index}" in used_ids:
        index += 1
    return f"{base}-{index}"


def _slug(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in value)
    parts = [part for part in normalized.split("-") if part]
    return "-".join(parts[:8])


def _parse_datetime(value: Any, *, all_day: bool) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    if len(text) == 10:
        try:
            return datetime.combine(date.fromisoformat(text), time.min)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if all_day:
        return datetime.combine(parsed.date(), time.min)
    return parsed.replace(tzinfo=None)


def _calendar_titles(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    raw_calendars = payload.get("calendars")
    if not isinstance(raw_calendars, list):
        return {}
    titles: dict[str, str] = {}
    for calendar in raw_calendars:
        if not isinstance(calendar, dict):
            continue
        calendar_id = _text(calendar.get("id"))
        title = _text(calendar.get("title") or calendar.get("name"))
        if calendar_id:
            titles[calendar_id] = title or calendar_id
    return titles


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _day_end(value: date) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min)


def _text(value: Any) -> str:
    return str(value or "").strip()
