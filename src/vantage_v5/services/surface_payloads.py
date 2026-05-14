from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.calendar import resolve_calendar_date
from vantage_v5.services.tasks import LocalTaskProvider


SURFACE_TODAY_BRIEFING = "today_briefing"
SURFACE_CALENDAR_DAY = "calendar_day"
SURFACE_CALENDAR_WEEK = "calendar_week"
SURFACE_TASK_FOCUS = "task_focus"
OPERATIONAL_SURFACES = {SURFACE_CALENDAR_DAY, SURFACE_CALENDAR_WEEK, SURFACE_TASK_FOCUS}
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


@dataclass(frozen=True, slots=True)
class SurfacePayloadResult:
    surface_payloads: list[dict[str, Any]]
    active_surface_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_payloads": self.surface_payloads,
            "active_surface_id": self.active_surface_id,
        }


class SurfacePayloadBuilder:
    def __init__(
        self,
        *,
        calendar_provider: LocalCalendarProvider,
        task_provider: LocalTaskProvider,
    ) -> None:
        self.calendar_provider = calendar_provider
        self.task_provider = task_provider

    def build_for_turn(
        self,
        *,
        message: str,
        surface_invocation: dict[str, Any] | None,
    ) -> SurfacePayloadResult:
        invocation = surface_invocation if isinstance(surface_invocation, dict) else {}
        requested_kinds = _requested_surface_kinds(invocation)
        if not requested_kinds:
            return SurfacePayloadResult(surface_payloads=[], active_surface_id=None)
        target_date = resolve_surface_date(message)
        calendar_week = self.calendar_provider.week(target_date) if SURFACE_CALENDAR_WEEK in requested_kinds else None
        calendar_day = self.calendar_provider.day(target_date) if SURFACE_CALENDAR_DAY in requested_kinds else None
        task_focus = self.task_provider.focus(target_date) if SURFACE_TASK_FOCUS in requested_kinds else None
        surfaces: list[dict[str, Any]] = []
        if calendar_week is not None:
            surfaces.append(build_calendar_week_surface(target_date=target_date, calendar_week=calendar_week.to_dict()))
        if calendar_day is not None and task_focus is not None and _should_build_today_briefing(invocation):
            surfaces.append(
                build_today_briefing_surface(
                    target_date=target_date,
                    calendar_day=calendar_day.to_dict(),
                    task_focus=task_focus.to_dict(),
                )
            )
        else:
            if calendar_day is not None:
                surfaces.append(build_calendar_surface(target_date=target_date, calendar_day=calendar_day.to_dict()))
            if task_focus is not None:
                surfaces.append(build_task_surface(target_date=target_date, task_focus=task_focus.to_dict()))
        return SurfacePayloadResult(
            surface_payloads=surfaces,
            active_surface_id=surfaces[0]["id"] if surfaces else None,
        )


def surface_assistant_message(surface_payloads: list[dict[str, Any]]) -> str | None:
    if not surface_payloads:
        return None
    surface = surface_payloads[0]
    kind = str(surface.get("kind") or "")
    data = surface.get("data") if isinstance(surface.get("data"), dict) else {}
    if kind == SURFACE_CALENDAR_WEEK:
        return _calendar_week_answer(data.get("calendar_week") if isinstance(data.get("calendar_week"), dict) else {})
    if kind == SURFACE_CALENDAR_DAY:
        return _calendar_day_answer(data.get("calendar") if isinstance(data.get("calendar"), dict) else {})
    if kind == SURFACE_TODAY_BRIEFING:
        return _today_briefing_answer(surface)
    if kind == SURFACE_TASK_FOCUS:
        return _task_focus_answer(data.get("tasks") if isinstance(data.get("tasks"), dict) else {})
    return None


def build_today_briefing_surface(
    *,
    target_date: date,
    calendar_day: dict[str, Any],
    task_focus: dict[str, Any],
) -> dict[str, Any]:
    suggestions = build_focus_suggestions(calendar_day=calendar_day, task_focus=task_focus)
    return {
        "id": f"today-{target_date.isoformat()}",
        "kind": SURFACE_TODAY_BRIEFING,
        "title": "Today",
        "summary": _today_summary(calendar_day=calendar_day, task_focus=task_focus, suggestions=suggestions),
        "source_refs": _source_refs(calendar_day=calendar_day, task_focus=task_focus),
        "data": {
            "date": target_date.isoformat(),
            "calendar": calendar_day,
            "tasks": task_focus,
            "suggestions": suggestions,
        },
    }


def build_calendar_surface(*, target_date: date, calendar_day: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"calendar-{target_date.isoformat()}",
        "kind": SURFACE_CALENDAR_DAY,
        "title": "Timeline",
        "summary": _calendar_summary(calendar_day),
        "source_refs": _source_refs(calendar_day=calendar_day, task_focus=None),
        "data": {
            "date": target_date.isoformat(),
            "calendar": calendar_day,
            "suggestions": [],
        },
    }


def build_calendar_week_surface(*, target_date: date, calendar_week: dict[str, Any]) -> dict[str, Any]:
    start_date = str(calendar_week.get("start_date") or target_date.isoformat())
    return {
        "id": f"calendar-week-{start_date}",
        "kind": SURFACE_CALENDAR_WEEK,
        "title": "Week",
        "summary": _calendar_week_summary(calendar_week),
        "source_refs": _source_refs(calendar_day=None, calendar_week=calendar_week, task_focus=None),
        "data": {
            "date": target_date.isoformat(),
            "calendar_week": calendar_week,
            "suggestions": [],
        },
    }


def build_task_surface(*, target_date: date, task_focus: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"tasks-{target_date.isoformat()}",
        "kind": SURFACE_TASK_FOCUS,
        "title": "Focus Stack",
        "summary": _task_summary(task_focus),
        "source_refs": _source_refs(calendar_day=None, task_focus=task_focus),
        "data": {
            "date": target_date.isoformat(),
            "tasks": task_focus,
            "suggestions": [],
        },
    }


def build_focus_suggestions(
    *,
    calendar_day: dict[str, Any],
    task_focus: dict[str, Any],
) -> list[dict[str, Any]]:
    free_blocks = [
        block for block in calendar_day.get("free_blocks", [])
        if isinstance(block, dict) and int(block.get("duration_minutes") or 0) >= 30
    ]
    tasks = _suggestable_tasks(task_focus)
    suggestions: list[dict[str, Any]] = []
    for index, task in enumerate(tasks[: len(free_blocks)]):
        block = free_blocks[index]
        duration = int(task.get("duration_minutes") or 0) or min(90, int(block.get("duration_minutes") or 60))
        suggestions.append(
            {
                "id": f"suggestion-{task.get('id') or index + 1}",
                "task_id": task.get("id"),
                "task_title": task.get("title") or "Focus task",
                "start": block.get("start"),
                "end": block.get("end"),
                "duration_minutes": duration,
                "reason": _suggestion_reason(index=index, duration=duration),
                "source": "surface_payload_builder",
            }
        )
    return suggestions


def resolve_surface_date(message: str) -> date:
    text = str(message or "")
    iso_match = ISO_DATE_RE.search(text)
    if iso_match:
        return resolve_calendar_date(iso_match.group(0))
    lowered = text.lower()
    for phrase in ("tomorrow", "yesterday", "today"):
        if phrase in lowered:
            return resolve_calendar_date(phrase)
    return resolve_calendar_date("today")


def _requested_surface_kinds(invocation: dict[str, Any]) -> list[str]:
    kinds = [
        str(invocation.get("primary_surface") or "").strip().lower(),
        *[
            str(kind or "").strip().lower()
            for kind in invocation.get("supporting_surfaces") or []
        ],
    ]
    return [
        kind
        for kind in dict.fromkeys(kinds)
        if kind in OPERATIONAL_SURFACES
    ]


def _should_build_today_briefing(invocation: dict[str, Any]) -> bool:
    intent = str(invocation.get("intent") or "").strip().lower()
    primary = str(invocation.get("primary_surface") or "").strip().lower()
    return primary == SURFACE_CALENDAR_DAY and intent in {"schedule_lookup", "schedule_planning"}


def _suggestable_tasks(task_focus: dict[str, Any]) -> list[dict[str, Any]]:
    groups = task_focus.get("groups") if isinstance(task_focus.get("groups"), dict) else {}
    tasks: list[dict[str, Any]] = []
    for key in ("must_do_today", "good_next", "unscheduled", "can_defer"):
        tasks.extend([task for task in groups.get(key, []) if isinstance(task, dict)])
    return tasks


def _today_summary(
    *,
    calendar_day: dict[str, Any],
    task_focus: dict[str, Any],
    suggestions: list[dict[str, Any]],
) -> str:
    event_count = int(calendar_day.get("summary", {}).get("event_count") or 0)
    open_minutes = int(calendar_day.get("summary", {}).get("free_minutes") or 0)
    focus_count = len(suggestions) or int(task_focus.get("summary", {}).get("must_do_today_count") or 0)
    return f"{event_count} scheduled events, {focus_count} focus blocks, {_format_hours(open_minutes)} open."


def _calendar_summary(calendar_day: dict[str, Any]) -> str:
    summary = calendar_day.get("summary") if isinstance(calendar_day.get("summary"), dict) else {}
    return f"{int(summary.get('event_count') or 0)} scheduled events, {_format_hours(int(summary.get('free_minutes') or 0))} open."


def _calendar_week_summary(calendar_week: dict[str, Any]) -> str:
    summary = calendar_week.get("summary") if isinstance(calendar_week.get("summary"), dict) else {}
    event_count = int(summary.get("event_count") or 0)
    free_minutes = int(summary.get("free_minutes") or 0)
    return f"{event_count} scheduled events this week, {_format_hours(free_minutes)} open."


def _calendar_week_answer(calendar_week: dict[str, Any]) -> str:
    summary = calendar_week.get("summary") if isinstance(calendar_week.get("summary"), dict) else {}
    source = calendar_week.get("source") if isinstance(calendar_week.get("source"), dict) else {}
    event_count = int(summary.get("event_count") or 0)
    free_minutes = int(summary.get("free_minutes") or 0)
    range_label = _date_range_label(str(calendar_week.get("start_date") or ""), str(calendar_week.get("end_date") or ""))
    if not source.get("configured"):
        return f"I opened your week calendar for {range_label}. No local calendar file is configured yet, so the view is showing open work blocks only."
    if event_count == 0:
        return f"I opened your week calendar for {range_label}. You do not have scheduled events in the local calendar file, with {_format_hours(free_minutes)} open across the workweek."
    highlights = _event_highlights(calendar_week)
    suffix = f" First up: {highlights}." if highlights else ""
    return f"I opened your week calendar for {range_label}. You have {event_count} scheduled event{'s' if event_count != 1 else ''} and {_format_hours(free_minutes)} open across the workweek.{suffix}"


def _calendar_day_answer(calendar_day: dict[str, Any]) -> str:
    summary = calendar_day.get("summary") if isinstance(calendar_day.get("summary"), dict) else {}
    source = calendar_day.get("source") if isinstance(calendar_day.get("source"), dict) else {}
    event_count = int(summary.get("event_count") or 0)
    free_minutes = int(summary.get("free_minutes") or 0)
    date_label = str(calendar_day.get("date") or "today")
    if not source.get("configured"):
        return f"I opened your calendar for {date_label}. No local calendar file is configured yet, so the timeline is showing open work blocks only."
    if event_count == 0:
        return f"I opened your calendar for {date_label}. You do not have scheduled events in the local calendar file, with {_format_hours(free_minutes)} open."
    return f"I opened your calendar for {date_label}. You have {event_count} scheduled event{'s' if event_count != 1 else ''} and {_format_hours(free_minutes)} open."


def _today_briefing_answer(surface: dict[str, Any]) -> str:
    data = surface.get("data") if isinstance(surface.get("data"), dict) else {}
    calendar_day = data.get("calendar") if isinstance(data.get("calendar"), dict) else {}
    task_focus = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    summary = calendar_day.get("summary") if isinstance(calendar_day.get("summary"), dict) else {}
    task_summary = task_focus.get("summary") if isinstance(task_focus.get("summary"), dict) else {}
    event_count = int(summary.get("event_count") or 0)
    task_count = int(task_summary.get("task_count") or 0)
    return f"I opened today's planning surface. I found {event_count} scheduled event{'s' if event_count != 1 else ''} and {task_count} open task{'s' if task_count != 1 else ''} in the local sources."


def _task_focus_answer(task_focus: dict[str, Any]) -> str:
    summary = task_focus.get("summary") if isinstance(task_focus.get("summary"), dict) else {}
    source = task_focus.get("source") if isinstance(task_focus.get("source"), dict) else {}
    task_count = int(summary.get("task_count") or 0)
    must_do_count = int(summary.get("must_do_today_count") or 0)
    if not source.get("configured"):
        return "I opened the task focus surface. No local task file is configured yet, so there are no tasks to group."
    return f"I opened your task focus surface. I found {task_count} open task{'s' if task_count != 1 else ''}, including {must_do_count} must-do item{'s' if must_do_count != 1 else ''} for today."


def _date_range_label(start_date: str, end_date: str) -> str:
    if not start_date or not end_date:
        return "this week"
    return f"{start_date} through {end_date}"


def _event_highlights(calendar_week: dict[str, Any]) -> str:
    days = calendar_week.get("days") if isinstance(calendar_week.get("days"), list) else []
    events: list[dict[str, Any]] = []
    for day in days:
        if not isinstance(day, dict):
            continue
        events.extend([event for event in day.get("events", []) if isinstance(event, dict)])
    titles = [str(event.get("title") or "Calendar event").strip() for event in events[:3]]
    return ", ".join(title for title in titles if title)


def _task_summary(task_focus: dict[str, Any]) -> str:
    summary = task_focus.get("summary") if isinstance(task_focus.get("summary"), dict) else {}
    return f"{int(summary.get('task_count') or 0)} open tasks, {int(summary.get('must_do_today_count') or 0)} must do today."


def _source_refs(
    *,
    calendar_day: dict[str, Any] | None,
    calendar_week: dict[str, Any] | None = None,
    task_focus: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if calendar_day is not None:
        refs.append(
            {
                "kind": "calendar_day",
                "label": calendar_day.get("source", {}).get("label") or "Calendar",
                "configured": bool(calendar_day.get("source", {}).get("configured")),
                "read_only": True,
                "count": int(calendar_day.get("summary", {}).get("event_count") or 0),
            }
        )
    if calendar_week is not None:
        refs.append(
            {
                "kind": "calendar_week",
                "label": calendar_week.get("source", {}).get("label") or "Calendar",
                "configured": bool(calendar_week.get("source", {}).get("configured")),
                "read_only": True,
                "count": int(calendar_week.get("summary", {}).get("event_count") or 0),
            }
        )
    if task_focus is not None:
        refs.append(
            {
                "kind": "task_focus",
                "label": task_focus.get("source", {}).get("label") or "Tasks",
                "configured": bool(task_focus.get("source", {}).get("configured")),
                "read_only": True,
                "count": int(task_focus.get("summary", {}).get("task_count") or 0),
            }
        )
    return refs


def _suggestion_reason(*, index: int, duration: int) -> str:
    if index == 0:
        return f"Best focus window for a {duration}-minute block."
    if duration >= 90:
        return "High-impact open block with enough room for deep work."
    return "Good stretch of open time."


def _format_hours(minutes: int) -> str:
    if minutes <= 0:
        return "0 hours"
    hours = minutes / 60
    if minutes % 60 == 0:
        return f"{int(hours)} hour{'s' if hours != 1 else ''}"
    return f"{hours:.1f} hours"
