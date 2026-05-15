from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from vantage_v5.services.tasks import LocalTaskProvider
from vantage_v5.services.tasks import TaskItem
from vantage_v5.services.tasks import group_tasks_for_focus


def test_group_tasks_for_focus_prioritizes_due_and_high_priority_items() -> None:
    groups = group_tasks_for_focus(
        [
            TaskItem(id="overdue", title="Overdue", due_date=date(2026, 5, 12), priority="normal"),
            TaskItem(id="today", title="Today", due_date=date(2026, 5, 13), priority="low"),
            TaskItem(id="high", title="High priority no date", priority="high"),
            TaskItem(id="tomorrow", title="Tomorrow", due_date=date(2026, 5, 14), priority="normal"),
            TaskItem(id="later", title="Later", due_date=date(2026, 5, 21), priority="low"),
            TaskItem(id="unscheduled", title="Unscheduled", priority="normal"),
        ],
        target_date=date(2026, 5, 13),
    )

    assert [task.id for task in groups["must_do_today"]] == ["high", "overdue", "today"]
    assert [task.id for task in groups["good_next"]] == ["tomorrow"]
    assert [task.id for task in groups["can_defer"]] == ["later"]
    assert [task.id for task in groups["unscheduled"]] == ["unscheduled"]


def test_local_task_provider_reads_json_and_filters_closed_tasks(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {"id": "homework", "title": "Homework", "due": "2026-05-13", "priority": "high"},
                    {"id": "done", "title": "Done task", "status": "done"},
                    {"title": "Reading", "priority": "low"},
                ]
            }
        ),
        encoding="utf-8",
    )
    provider = LocalTaskProvider(tasks_path=tasks_path)

    focus = provider.focus(date(2026, 5, 13)).to_dict()

    assert focus["source"]["configured"] is True
    assert focus["summary"]["task_count"] == 2
    assert [task["id"] for task in focus["groups"]["must_do_today"]] == ["homework"]
    assert [task["title"] for task in focus["groups"]["can_defer"]] == ["Reading"]


def test_local_task_provider_treats_missing_file_as_empty(tmp_path: Path) -> None:
    provider = LocalTaskProvider(tasks_path=tmp_path / "missing.json")

    focus = provider.focus(date(2026, 5, 13)).to_dict()

    assert focus["source"]["configured"] is False
    assert focus["summary"]["task_count"] == 0


def test_local_task_provider_creates_task_when_user_scoped_store_is_writable(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "meta": {"owner": "eden"},
                "tasks": [{"id": "existing", "title": "Existing task", "custom": "keep"}],
            }
        ),
        encoding="utf-8",
    )
    provider = LocalTaskProvider(tasks_path=tasks_path, writable=True)

    result = provider.create_task(title="Finish homework 2", due_date=date(2026, 5, 14), priority="high")

    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert result["summary"] == "Created task 'Finish homework 2'."
    assert payload["meta"] == {"owner": "eden"}
    assert payload["tasks"][0]["custom"] == "keep"
    assert payload["tasks"][1]["title"] == "Finish homework 2"
    assert payload["tasks"][1]["due_date"] == "2026-05-14"


def test_local_task_provider_blocks_writes_when_read_only(tmp_path: Path) -> None:
    provider = LocalTaskProvider(tasks_path=tmp_path / "tasks.json", writable=False)

    try:
        provider.create_task(title="Blocked")
    except PermissionError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("Expected read-only task provider to reject writes.")
