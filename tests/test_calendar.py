from __future__ import annotations

from datetime import date
from datetime import datetime
from pathlib import Path
import json

from vantage_v5.services.calendar import compute_free_blocks
from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.calendar import resolve_calendar_date
from vantage_v5.services.calendar import week_start_for


def test_resolve_calendar_date_supports_relative_and_iso_dates() -> None:
    today = date(2026, 5, 13)

    assert resolve_calendar_date(None, today=today) == today
    assert resolve_calendar_date("today", today=today) == today
    assert resolve_calendar_date("tomorrow", today=today) == date(2026, 5, 14)
    assert resolve_calendar_date("yesterday", today=today) == date(2026, 5, 12)
    assert resolve_calendar_date("2026-06-01", today=today) == date(2026, 6, 1)


def test_local_calendar_provider_groups_day_events_and_free_blocks(tmp_path: Path) -> None:
    events_path = _write_calendar_events(
        tmp_path / "events.json",
        events=[
            {
                "id": "study",
                "calendar_id": "school",
                "title": "Midterm study",
                "start": "2026-05-13T14:00:00",
                "end": "2026-05-13T15:30:00",
                "location": "Library",
            },
            {
                "id": "standup",
                "calendar_id": "school",
                "title": "Project standup",
                "start": "2026-05-13T09:30:00",
                "end": "2026-05-13T10:00:00",
            },
            {
                "id": "tomorrow",
                "calendar_id": "school",
                "title": "Tomorrow event",
                "start": "2026-05-14T09:30:00",
                "end": "2026-05-14T10:00:00",
            },
        ],
    )
    provider = LocalCalendarProvider(events_path=events_path)

    calendar_day = provider.day(date(2026, 5, 13)).to_dict()

    assert calendar_day["date"] == "2026-05-13"
    assert calendar_day["source"] == {
        "kind": "local_json",
        "label": "Local calendar",
        "configured": True,
        "read_only": True,
        "event_count": 2,
    }
    assert [event["id"] for event in calendar_day["events"]] == ["standup", "study"]
    assert calendar_day["events"][0]["calendar_title"] == "School"
    assert calendar_day["events"][1]["location"] == "Library"
    assert calendar_day["summary"]["event_count"] == 2
    assert calendar_day["summary"]["free_block_count"] == 3
    assert [(block["start"], block["end"]) for block in calendar_day["free_blocks"]] == [
        ("2026-05-13T09:00:00", "2026-05-13T09:30:00"),
        ("2026-05-13T10:00:00", "2026-05-13T14:00:00"),
        ("2026-05-13T15:30:00", "2026-05-13T18:00:00"),
    ]


def test_compute_free_blocks_merges_overlapping_events_and_skips_all_day(tmp_path: Path) -> None:
    provider = LocalCalendarProvider(
        events_path=_write_calendar_events(
            tmp_path / "events.json",
            events=[
                {
                    "id": "all-day",
                    "title": "All day marker",
                    "start": "2026-05-13",
                    "end": "2026-05-14",
                    "all_day": True,
                },
                {
                    "id": "a",
                    "title": "A",
                    "start": "2026-05-13T09:00:00",
                    "end": "2026-05-13T10:30:00",
                },
                {
                    "id": "b",
                    "title": "B",
                    "start": "2026-05-13T10:00:00",
                    "end": "2026-05-13T11:00:00",
                },
            ],
        )
    )

    free_blocks = compute_free_blocks(
        target_date=date(2026, 5, 13),
        events=provider.day(date(2026, 5, 13)).events,
    )

    assert [(block.start.isoformat(), block.end.isoformat()) for block in free_blocks] == [
        ("2026-05-13T11:00:00", "2026-05-13T18:00:00"),
    ]


def test_local_calendar_provider_groups_week_events_by_day(tmp_path: Path) -> None:
    provider = LocalCalendarProvider(
        events_path=_write_calendar_events(
            tmp_path / "events.json",
            events=[
                {
                    "id": "monday",
                    "calendar_id": "school",
                    "title": "Monday lab",
                    "start": "2026-05-11T10:00:00",
                    "end": "2026-05-11T11:00:00",
                },
                {
                    "id": "wednesday",
                    "calendar_id": "school",
                    "title": "Wednesday lecture",
                    "start": "2026-05-13T14:00:00",
                    "end": "2026-05-13T15:00:00",
                },
                {
                    "id": "next-week",
                    "calendar_id": "school",
                    "title": "Next week",
                    "start": "2026-05-18T09:00:00",
                    "end": "2026-05-18T10:00:00",
                },
            ],
        )
    )

    calendar_week = provider.week(date(2026, 5, 13)).to_dict()

    assert calendar_week["start_date"] == "2026-05-11"
    assert calendar_week["end_date"] == "2026-05-17"
    assert calendar_week["summary"]["day_count"] == 7
    assert calendar_week["summary"]["event_count"] == 2
    assert calendar_week["source"]["event_count"] == 2
    assert [day["date"] for day in calendar_week["days"][:3]] == ["2026-05-11", "2026-05-12", "2026-05-13"]
    assert [event["id"] for event in calendar_week["days"][0]["events"]] == ["monday"]
    assert [event["id"] for event in calendar_week["days"][2]["events"]] == ["wednesday"]


def test_week_start_for_uses_monday_anchor() -> None:
    assert week_start_for(date(2026, 5, 11)) == date(2026, 5, 11)
    assert week_start_for(date(2026, 5, 17)) == date(2026, 5, 11)


def test_local_calendar_provider_updates_events_when_writable(tmp_path: Path) -> None:
    events_path = _write_calendar_events(
        tmp_path / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "calendar_id": "school",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
                "private_note": "preserve me",
            }
        ],
    )
    provider = LocalCalendarProvider(events_path=events_path, writable=True)

    result = provider.update_event("advisor-check-in", {"title": "Grocery shopping"})

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert result["before"]["title"] == "Advisor check-in"
    assert result["after"]["title"] == "Grocery shopping"
    assert payload["events"][0]["title"] == "Grocery shopping"
    assert payload["events"][0]["private_note"] == "preserve me"
    assert provider.day(date(2026, 5, 14)).to_dict()["source"]["writable"] is True


def test_local_calendar_provider_soft_cancels_events_without_deleting(tmp_path: Path) -> None:
    events_path = _write_calendar_events(
        tmp_path / "events.json",
        events=[
            {
                "id": "advisor-check-in",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            }
        ],
    )
    provider = LocalCalendarProvider(events_path=events_path, writable=True)

    provider.soft_cancel_event("advisor-check-in")

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["events"][0]["status"] == "cancelled"
    assert provider.day(date(2026, 5, 14)).events == ()


def test_local_calendar_provider_creates_events_when_writable(tmp_path: Path) -> None:
    events_path = _write_calendar_events(tmp_path / "events.json", events=[])
    provider = LocalCalendarProvider(events_path=events_path, writable=True)

    result = provider.create_event(
        title="Grocery shopping",
        start=datetime(2026, 5, 14, 11, 0),
        end=datetime(2026, 5, 14, 11, 30),
        calendar_id="personal",
    )

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert result["event_id"] == "grocery-shopping"
    assert payload["events"][0]["title"] == "Grocery shopping"
    assert payload["events"][0]["calendar_id"] == "personal"


def _write_calendar_events(path: Path, *, events: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "calendars": [{"id": "school", "title": "School"}],
                "events": events,
            }
        ),
        encoding="utf-8",
    )
    return path
