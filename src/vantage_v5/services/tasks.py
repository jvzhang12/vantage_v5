from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
import json
from pathlib import Path
from typing import Any


OPEN_TASK_STATUSES = {"", "open", "active", "todo", "to_do", "in_progress", "next"}
CLOSED_TASK_STATUSES = {"done", "completed", "complete", "cancelled", "canceled", "archived"}
HIGH_PRIORITY = {"urgent", "high", "must", "must_do", "p1"}
MEDIUM_PRIORITY = {"medium", "normal", "p2"}
LOW_PRIORITY = {"low", "defer", "later", "p3"}


@dataclass(frozen=True, slots=True)
class TaskItem:
    id: str
    title: str
    due_date: date | None = None
    status: str = "open"
    priority: str = "normal"
    project: str = ""
    notes: str = ""
    duration_minutes: int | None = None
    source: str = "local_tasks"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "priority": self.priority,
            "project": self.project,
            "notes": self.notes,
            "duration_minutes": self.duration_minutes,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class TaskFocus:
    date: date
    groups: dict[str, tuple[TaskItem, ...]]
    source: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        counts = {key: len(items) for key, items in self.groups.items()}
        return {
            "date": self.date.isoformat(),
            "source": dict(self.source),
            "groups": {
                key: [item.to_dict() for item in items]
                for key, items in self.groups.items()
            },
            "counts": counts,
            "summary": {
                "task_count": sum(counts.values()),
                "must_do_today_count": counts.get("must_do_today", 0),
                "good_next_count": counts.get("good_next", 0),
                "can_defer_count": counts.get("can_defer", 0),
                "unscheduled_count": counts.get("unscheduled", 0),
            },
        }


class LocalTaskProvider:
    def __init__(self, *, tasks_path: Path | None) -> None:
        self.tasks_path = tasks_path

    def focus(self, target_date: date) -> TaskFocus:
        tasks = [
            task
            for task in self._read_tasks()
            if _normalize_status(task.status) not in CLOSED_TASK_STATUSES
        ]
        groups = group_tasks_for_focus(tasks, target_date=target_date)
        return TaskFocus(
            date=target_date,
            groups=groups,
            source=self.source_status(task_count=len(tasks)),
        )

    def source_status(self, *, task_count: int | None = None) -> dict[str, Any]:
        configured = bool(self.tasks_path and self.tasks_path.exists())
        return {
            "kind": "local_json",
            "label": "Local tasks",
            "configured": configured,
            "read_only": True,
            "task_count": task_count,
        }

    def _read_tasks(self) -> list[TaskItem]:
        if not self.tasks_path or not self.tasks_path.exists():
            return []
        try:
            payload = json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        raw_tasks = payload.get("tasks") if isinstance(payload, dict) else payload
        if not isinstance(raw_tasks, list):
            return []
        tasks: list[TaskItem] = []
        for index, raw_task in enumerate(raw_tasks):
            task = _parse_task(raw_task, fallback_index=index)
            if task is not None:
                tasks.append(task)
        return tasks


def group_tasks_for_focus(
    tasks: list[TaskItem] | tuple[TaskItem, ...],
    *,
    target_date: date,
) -> dict[str, tuple[TaskItem, ...]]:
    groups: dict[str, list[TaskItem]] = {
        "must_do_today": [],
        "good_next": [],
        "can_defer": [],
        "unscheduled": [],
    }
    for task in tasks:
        groups[_focus_group_for_task(task, target_date=target_date)].append(task)
    return {
        key: tuple(sorted(items, key=_task_sort_key))
        for key, items in groups.items()
    }


def _focus_group_for_task(task: TaskItem, *, target_date: date) -> str:
    priority = _normalize_priority(task.priority)
    if task.due_date and task.due_date <= target_date:
        return "must_do_today"
    if priority in HIGH_PRIORITY:
        return "must_do_today"
    if task.due_date and task.due_date <= target_date + timedelta(days=2):
        return "good_next"
    if task.due_date:
        return "can_defer" if priority in LOW_PRIORITY else "good_next"
    if priority in LOW_PRIORITY:
        return "can_defer"
    return "unscheduled"


def _task_sort_key(task: TaskItem) -> tuple[int, date, str]:
    priority = _normalize_priority(task.priority)
    if priority in HIGH_PRIORITY:
        priority_rank = 0
    elif priority in MEDIUM_PRIORITY:
        priority_rank = 1
    elif priority in LOW_PRIORITY:
        priority_rank = 3
    else:
        priority_rank = 2
    return (priority_rank, task.due_date or date.max, task.title.lower())


def _parse_task(raw_task: Any, *, fallback_index: int) -> TaskItem | None:
    if not isinstance(raw_task, dict):
        return None
    title = _text(raw_task.get("title") or raw_task.get("name") or raw_task.get("summary"))
    if not title:
        return None
    status = _normalize_status(raw_task.get("status") or ("completed" if raw_task.get("completed") else "open"))
    return TaskItem(
        id=_text(raw_task.get("id") or f"local-task-{fallback_index + 1}"),
        title=title,
        due_date=_parse_date(raw_task.get("due_date") or raw_task.get("dueDate") or raw_task.get("due")),
        status=status if status in OPEN_TASK_STATUSES | CLOSED_TASK_STATUSES else "open",
        priority=_normalize_priority(raw_task.get("priority") or raw_task.get("importance") or "normal"),
        project=_text(raw_task.get("project") or raw_task.get("list") or raw_task.get("area")),
        notes=_text(raw_task.get("notes") or raw_task.get("description")),
        duration_minutes=_parse_duration(raw_task.get("duration_minutes") or raw_task.get("durationMinutes")),
    )


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_duration(value: Any) -> int | None:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def _normalize_status(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_priority(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _text(value: Any) -> str:
    return str(value or "").strip()
