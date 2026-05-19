from __future__ import annotations

from pathlib import Path
import json

from vantage_v5.services.artifact_actions import ArtifactActionPlanner
from vantage_v5.services.artifact_actions import ArtifactActionStore
from vantage_v5.services.artifact_actions import execute_artifact_action
from vantage_v5.services.artifact_mutation_compiler import ArtifactMutationCompiler
from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.tasks import LocalTaskProvider


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


def test_calendar_action_planner_can_return_unsaved_proposal_candidate(tmp_path: Path) -> None:
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
    action_store = ArtifactActionStore(tmp_path / "actions")
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
        action_store=action_store,
    )

    candidate = planner.plan_for_turn(
        message="replace Advisor check-in with Grocery shopping",
        visible_artifacts=[_today_surface()],
        persist=False,
    )

    assert len(candidate.artifact_actions) == 1
    action = candidate.artifact_actions[0]
    assert not (tmp_path / "actions" / f"{action['id']}.json").exists()

    saved = planner.save_action_plan(candidate)

    assert saved.artifact_actions[0]["id"] == action["id"]
    assert (tmp_path / "actions" / f"{action['id']}.json").exists()
    assert "after you confirm" in saved.assistant_message


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


def test_calendar_capture_statement_proposes_create_event_without_mutating(tmp_path: Path) -> None:
    events_path = _write_calendar_events(tmp_path / "events.json", events=[])
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="I have office hours at 3 2026-05-14",
        visible_artifacts=[],
    )

    assert len(result.artifact_actions) == 1
    action = result.artifact_actions[0]
    assert action["artifact_kind"] == "calendar"
    assert action["operation"] == "create_event"
    assert action["payload"]["title"] == "office hours"
    assert action["payload"]["start"] == "2026-05-14T15:00:00"
    assert action["payload"]["end"] == "2026-05-14T15:30:00"
    assert action["payload"]["capture"]["kind"] == "calendar_statement"
    assert json.loads(events_path.read_text(encoding="utf-8"))["events"] == []


def test_calendar_capture_event_called_phrase_proposes_create_event_without_mutating(tmp_path: Path) -> None:
    events_path = _write_calendar_events(tmp_path / "events.json", events=[])
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=events_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="Add a calendar event tomorrow at 3 PM called Graph study review.",
        visible_artifacts=[],
    )

    assert len(result.artifact_actions) == 1
    action = result.artifact_actions[0]
    assert action["artifact_kind"] == "calendar"
    assert action["operation"] == "create_event"
    assert action["status"] == "proposed"
    assert action["requires_confirmation"] is True
    assert action["payload"]["title"] == "Graph study review"
    assert action["payload"]["start"].endswith("T15:00:00")
    assert action["payload"]["end"].endswith("T15:30:00")
    assert json.loads(events_path.read_text(encoding="utf-8"))["events"] == []


def test_calendar_lookup_phrase_does_not_become_capture(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="Show me my calendar tomorrow at 3 PM.",
        visible_artifacts=[],
    )

    assert result.artifact_actions == []


def test_compiler_marks_model_normalized_source_when_normalized_command_succeeds(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    compiler = ArtifactMutationCompiler(planner=planner, app_capabilities={}, model="test")
    compiler._normalize_with_model = lambda **kwargs: "Add Graph study review at 3 PM tomorrow."  # type: ignore[method-assign]

    result = compiler.compile_for_turn(
        user_message="Add a calendar event tomorrow at 3 PM called Graph study review.",
        semantic_action="I will add that calendar event.",
        visible_artifacts=[],
        persist=False,
    )

    assert len(result.artifact_actions) == 1
    compiler_metadata = result.artifact_actions[0]["compiler"]
    assert compiler_metadata["source"] == "model_normalized"
    assert compiler_metadata["model_normalized"] is True
    assert compiler_metadata["compiler_input"] == "Add Graph study review at 3 PM tomorrow."


def test_compiler_marks_raw_message_fallback_source_when_normalized_command_fails(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    compiler = ArtifactMutationCompiler(planner=planner, app_capabilities={}, model="test")
    compiler._normalize_with_model = lambda **kwargs: "Show me my calendar tomorrow at 3 PM."  # type: ignore[method-assign]

    result = compiler.compile_for_turn(
        user_message="Add a calendar event tomorrow at 3 PM called Graph study review.",
        semantic_action="I will add that calendar event.",
        visible_artifacts=[],
        persist=False,
    )

    assert len(result.artifact_actions) == 1
    compiler_metadata = result.artifact_actions[0]["compiler"]
    assert compiler_metadata["source"] == "deterministic_fallback"
    assert compiler_metadata["model_normalized"] is False
    assert compiler_metadata["compiler_input"] == "Add a calendar event tomorrow at 3 PM called Graph study review."


def test_calendar_capture_missing_time_asks_for_clarification(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="I have office hours 2026-05-14",
        visible_artifacts=[],
    )

    assert result.artifact_actions == []
    assert result.error == "missing_calendar_time"
    assert "need a time" in result.assistant_message


def test_task_capture_statement_proposes_create_task_without_mutating(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="I need to finish homework 2 by 2026-05-14",
        visible_artifacts=[],
    )

    assert len(result.artifact_actions) == 1
    action = result.artifact_actions[0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "create_task"
    assert action["payload"]["title"] == "finish homework 2"
    assert action["payload"]["due_date"] == "2026-05-14"
    assert action["payload"]["capture"]["kind"] == "task_statement"
    assert not tasks_path.exists()


def test_task_capture_preserves_meaningful_leading_create_verbs(tmp_path: Path) -> None:
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tmp_path / "tasks.json", writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    examples = {
        "Add a task to create slides tonight.": "create slides",
        "Remember to create slides tomorrow.": "create slides",
        "I need to create slides tomorrow.": "create slides",
    }

    for message, expected_prefix in examples.items():
        result = planner.plan_for_turn(message=message, visible_artifacts=[], persist=False)

        assert len(result.artifact_actions) == 1
        action = result.artifact_actions[0]
        assert action["artifact_kind"] == "task"
        assert action["operation"] == "create_task"
        assert str(action["payload"]["title"]).startswith(expected_prefix)


def test_task_action_planner_proposes_complete_from_visible_task_list(tmp_path: Path) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks.json",
        tasks=[
            {
                "id": "homework-2",
                "title": "Finish Homework 2",
                "due_date": "2026-05-14",
                "status": "open",
            }
        ],
    )
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )

    result = planner.plan_for_turn(
        message="mark Homework 2 done",
        visible_artifacts=[_task_surface()],
    )

    assert len(result.artifact_actions) == 1
    action = result.artifact_actions[0]
    assert action["artifact_kind"] == "task"
    assert action["operation"] == "complete_task"
    assert action["payload"]["task_id"] == "homework-2"
    assert action["target_refs"][0]["title"] == "Finish Homework 2"


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


def test_execute_task_action_commits_proposed_create(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    action = planner.plan_for_turn(
        message="I need to finish homework 2 by 2026-05-14",
        visible_artifacts=[],
    ).artifact_actions[0]

    accepted = execute_artifact_action(
        action=action,
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
    )

    assert accepted["status"] == "accepted"
    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert payload["tasks"][0]["title"] == "finish homework 2"
    assert payload["tasks"][0]["due_date"] == "2026-05-14"


def test_execute_task_action_commits_proposed_complete(tmp_path: Path) -> None:
    tasks_path = _write_tasks(
        tmp_path / "tasks.json",
        tasks=[
            {
                "id": "homework-2",
                "title": "Finish Homework 2",
                "due_date": "2026-05-14",
                "status": "open",
                "custom": "preserved",
            }
        ],
    )
    planner = ArtifactActionPlanner(
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
        action_store=ArtifactActionStore(tmp_path / "actions"),
    )
    action = planner.plan_for_turn(
        message="mark Homework 2 done",
        visible_artifacts=[_task_surface()],
    ).artifact_actions[0]

    accepted = execute_artifact_action(
        action=action,
        calendar_provider=LocalCalendarProvider(events_path=tmp_path / "events.json", writable=True),
        task_provider=LocalTaskProvider(tasks_path=tasks_path, writable=True),
    )

    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert accepted["status"] == "accepted"
    assert payload["tasks"][0]["status"] == "completed"
    assert payload["tasks"][0]["custom"] == "preserved"


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


def _task_surface() -> dict[str, object]:
    return {
        "id": "tasks-2026-05-14",
        "kind": "task_focus",
        "title": "Today Focus",
        "summary": "1 open task.",
        "data": {
            "date": "2026-05-14",
            "tasks": {
                "date": "2026-05-14",
                "groups": {
                    "must_do_today": [
                        {
                            "id": "homework-2",
                            "title": "Finish Homework 2",
                            "due_date": "2026-05-14",
                            "status": "open",
                        }
                    ],
                    "good_next": [],
                    "can_defer": [],
                    "unscheduled": [],
                },
            },
        },
    }


def _write_calendar_events(path: Path, *, events: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"calendars": [{"id": "local", "title": "Calendar"}], "events": events}), encoding="utf-8")
    return path


def _write_tasks(path: Path, *, tasks: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    return path
