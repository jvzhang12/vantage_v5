from __future__ import annotations

from datetime import date

from vantage_v5.services.calendar import CalendarDay
from vantage_v5.services.calendar import CalendarEvent
from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.surface_payloads import SurfacePayloadBuilder
from vantage_v5.services.surface_payloads import build_focus_suggestions
from vantage_v5.services.surface_payloads import resolve_surface_date
from vantage_v5.services.surface_payloads import surface_assistant_message
from vantage_v5.services.tasks import LocalTaskProvider
from vantage_v5.services.tasks import TaskFocus
from vantage_v5.services.tasks import TaskItem


def test_resolve_surface_date_accepts_iso_date_inside_message() -> None:
    assert resolve_surface_date("Plan 2026-05-13 for me") == date(2026, 5, 13)


def test_build_focus_suggestions_pairs_must_do_tasks_with_free_blocks() -> None:
    calendar_day = CalendarDay(
        date=date(2026, 5, 13),
        events=(),
        free_blocks=(),
        source={"label": "Local calendar", "configured": True},
    ).to_dict()
    calendar_day["free_blocks"] = [
        {"start": "2026-05-13T10:00:00", "end": "2026-05-13T11:30:00", "duration_minutes": 90}
    ]
    task_focus = TaskFocus(
        date=date(2026, 5, 13),
        groups={
            "must_do_today": (TaskItem(id="homework", title="Homework", duration_minutes=75),),
            "good_next": (),
            "can_defer": (),
            "unscheduled": (),
        },
        source={"label": "Local tasks", "configured": True},
    ).to_dict()

    suggestions = build_focus_suggestions(calendar_day=calendar_day, task_focus=task_focus)

    assert suggestions == [
        {
            "id": "suggestion-homework",
            "task_id": "homework",
            "task_title": "Homework",
            "start": "2026-05-13T10:00:00",
            "end": "2026-05-13T11:30:00",
            "duration_minutes": 75,
            "reason": "Best focus window for a 75-minute block.",
            "source": "surface_payload_builder",
        }
    ]


def test_surface_payload_builder_creates_today_briefing_for_calendar_plus_tasks() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="Tell me about what I have planned for today on 2026-05-13.",
        surface_invocation={
            "intent": "schedule_lookup",
            "primary_surface": "calendar_day",
            "supporting_surfaces": ["task_focus"],
        },
    ).to_dict()

    assert result["active_surface_id"] == "today-2026-05-13"
    assert result["surface_payloads"][0]["kind"] == "today_briefing"


def test_surface_payload_builder_creates_today_briefing_from_attention_primary() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="What should I do today on 2026-05-13?",
        surface_invocation={
            "intent": "attention_selected_context",
            "primary_surface": "today_briefing",
            "supporting_surfaces": ["calendar_day", "task_focus"],
            "trigger": "attention_navigator",
        },
    ).to_dict()

    assert result["active_surface_id"] == "today-2026-05-13"
    assert result["surface_payloads"][0]["kind"] == "today_briefing"


def test_surface_payload_builder_keeps_attention_primary_surface_first() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="Show what to focus on today on 2026-05-13.",
        surface_invocation={
            "intent": "attention_selected_context",
            "primary_surface": "task_focus",
            "supporting_surfaces": ["calendar_day"],
            "trigger": "attention_navigator",
        },
    ).to_dict()

    assert result["active_surface_id"] == "tasks-2026-05-13"
    assert [surface["kind"] for surface in result["surface_payloads"]] == ["task_focus", "calendar_day"]


def test_surface_payload_source_refs_reflect_provider_write_capability(tmp_path) -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tmp_path / "tasks.json", writable=True),
    )

    result = builder.build_for_turn(
        message="Tell me about today on 2026-05-13.",
        surface_invocation={
            "intent": "schedule_lookup",
            "primary_surface": "calendar_day",
            "supporting_surfaces": ["task_focus"],
        },
    ).to_dict()

    refs = {ref["kind"]: ref for ref in result["surface_payloads"][0]["source_refs"]}
    assert refs["calendar_day"]["writable"] is True
    assert refs["calendar_day"]["read_only"] is False
    assert refs["calendar_day"]["capability_ref"] == "calendar.day"
    assert refs["task_focus"]["writable"] is True
    assert refs["task_focus"]["read_only"] is False
    assert refs["task_focus"]["capability_ref"] == "tasks.focus"


def test_surface_payload_builder_creates_calendar_week_payload() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="Show me my calendar for this week on 2026-05-13.",
        surface_invocation={
            "intent": "schedule_lookup",
            "primary_surface": "calendar_week",
            "supporting_surfaces": [],
        },
    ).to_dict()

    assert result["active_surface_id"] == "calendar-week-2026-05-11"
    assert result["surface_payloads"][0]["kind"] == "calendar_week"
    assert result["surface_payloads"][0]["data"]["calendar_week"]["start_date"] == "2026-05-11"
    assert result["surface_payloads"][0]["source_refs"][0]["kind"] == "calendar_week"


def test_surface_assistant_message_summarizes_calendar_week() -> None:
    payload = {
        "kind": "calendar_week",
        "data": {
            "calendar_week": {
                "start_date": "2026-05-11",
                "end_date": "2026-05-17",
                "source": {"configured": True},
                "summary": {"event_count": 1, "free_minutes": 540},
                "days": [
                    {
                        "events": [
                            {"title": "Algorithms lab", "start": "2026-05-11T10:00:00", "end": "2026-05-11T11:00:00"}
                        ]
                    }
                ],
            }
        },
    }

    message = surface_assistant_message([payload])

    assert message is not None
    assert "opened your week calendar" in message
    assert "1 scheduled event" in message
    assert "Algorithms lab" in message


def test_surface_payload_builder_skips_non_operational_surfaces() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="Write an email.",
        surface_invocation={"intent": "durable_artifact", "primary_surface": "whiteboard"},
    ).to_dict()

    assert result == {"surface_payloads": [], "active_surface_id": None}


def test_surface_payload_builder_does_not_render_supporting_operational_surface_for_whiteboard_primary() -> None:
    builder = SurfacePayloadBuilder(
        calendar_provider=LocalCalendarProvider(events_path=None),
        task_provider=LocalTaskProvider(tasks_path=None),
    )

    result = builder.build_for_turn(
        message="Find my midterm study material.",
        surface_invocation={
            "intent": "attention_selected_context",
            "primary_surface": "whiteboard",
            "supporting_surfaces": ["task_focus"],
        },
    ).to_dict()

    assert result == {"surface_payloads": [], "active_surface_id": None}
