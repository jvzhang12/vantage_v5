from __future__ import annotations

from pathlib import Path
import json

from vantage_v5.services.artifact_actions import ArtifactActionPlanner
from vantage_v5.services.artifact_actions import ArtifactActionStore
from vantage_v5.services.artifact_actions import execute_artifact_action
from vantage_v5.services.calendar import LocalCalendarProvider


def test_calendar_action_planner_proposes_replace_from_visible_calendar(tmp_path: Path) -> None:
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
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="replace Advisor check-in with Grocery shopping",
        visible_artifacts=[_today_surface()],
    )

    assert len(result.artifact_actions) == 1
    action = result.artifact_actions[0]
    assert action["artifact_kind"] == "calendar"
    assert action["operation"] == "replace_event"
    assert action["status"] == "proposed"
    assert action["payload"]["event_id"] == "advisor-check-in"
    assert action["payload"]["updates"] == {"title": "Grocery shopping"}
    assert "after you confirm" in result.assistant_message
    assert json.loads(events_path.read_text(encoding="utf-8"))["events"][0]["title"] == "Advisor check-in"


def test_calendar_action_planner_rejects_ambiguous_visible_event_matches(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    surface = _today_surface(
        events=[
            {
                "id": "advisor-1",
                "title": "Advisor check-in",
                "start": "2026-05-14T11:00:00",
                "end": "2026-05-14T11:30:00",
            },
            {
                "id": "advisor-2",
                "title": "Advisor check-in follow-up",
                "start": "2026-05-14T12:00:00",
                "end": "2026-05-14T12:30:00",
            },
        ]
    )

    result = planner.plan_for_turn(
        message="replace Advisor check-in with Grocery shopping",
        visible_artifacts=[surface],
    )

    assert result.artifact_actions == []
    assert result.error == "ambiguous_target"
    assert "more than one calendar event" in result.assistant_message


def test_calendar_action_planner_keeps_read_only_global_calendar_restricted(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=False),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="replace Advisor check-in with Grocery shopping",
        visible_artifacts=[_today_surface()],
    )

    assert result.artifact_actions == []
    assert result.error == "calendar_read_only"
    assert "read-only" in result.assistant_message


def test_execute_calendar_action_commits_proposed_replace(tmp_path: Path) -> None:
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
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    action = planner.plan_for_turn(
        message="replace Advisor check-in with Grocery shopping",
        visible_artifacts=[_today_surface()],
    ).artifact_actions[0]

    accepted = execute_artifact_action(
        action=action,
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
    )

    assert accepted["status"] == "accepted"
    assert json.loads(events_path.read_text(encoding="utf-8"))["events"][0]["title"] == "Grocery shopping"


def _today_surface(*, events: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "id": "today-2026-05-14",
        "kind": "today_briefing",
        "title": "Today",
        "summary": "1 scheduled event.",
        "data": {
            "date": "2026-05-14",
            "calendar": {
                "date": "2026-05-14",
                "events": events
                or [
                    {
                        "id": "advisor-check-in",
                        "title": "Advisor check-in",
                        "start": "2026-05-14T11:00:00",
                        "end": "2026-05-14T11:30:00",
                    }
                ],
                "free_blocks": [],
            },
        },
    }


def _write_calendar_events(path: Path, *, events: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"calendars": [{"id": "local", "title": "Calendar"}], "events": events}), encoding="utf-8")
    return path
