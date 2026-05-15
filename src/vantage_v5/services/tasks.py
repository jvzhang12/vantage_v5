from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
import json
from pathlib import Path
import re
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
    def __init__(self, *, tasks_path: Path | None, writable: bool = False) -> None:
        self.tasks_path = tasks_path
        self.writable = writable

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
        writable = bool(self.writable and self.tasks_path)
        status = {
            "kind": "local_json",
            "label": "Local tasks",
            "configured": configured,
            "read_only": not writable,
            "task_count": task_count,
        }
        if writable:
            status["writable"] = True
        return status

    def create_task(
        self,
        *,
        title: str,
        due_date: date | None = None,
        status: str = "open",
        priority: str = "normal",
        project: str = "",
        notes: str = "",
        duration_minutes: int | None = None,
    ) -> dict[str, Any]:
        self._ensure_writable()
        payload = self._read_payload()
        tasks = _raw_task_records(payload)
        raw_task: dict[str, Any] = {
            "id": _next_task_id(tasks, title=title),
            "title": title.strip() or "Untitled task",
            "status": _normalize_status(status) or "open",
            "priority": _normalize_priority(priority) or "normal",
        }
        if due_date:
            raw_task["due_date"] = due_date.isoformat()
        if project:
            raw_task["project"] = project
        if notes:
            raw_task["notes"] = notes
        if duration_minutes and duration_minutes > 0:
            raw_task["duration_minutes"] = int(duration_minutes)
        tasks.append(raw_task)
        self._write_payload(payload)
        return {
            "before": None,
            "after": raw_task,
            "task_id": raw_task["id"],
            "summary": f"Created task '{raw_task['title']}'.",
        }

    def update_task(self, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        self._ensure_writable()
        payload = self._read_payload()
        task = _find_raw_task(payload, task_id)
        before = dict(task)
        for key in ["title", "status", "priority", "project", "notes", "duration_minutes", "durationMinutes"]:
            if key in updates:
                task[key] = updates[key]
        if "due_date" in updates:
            task["due_date"] = updates["due_date"]
        if "dueDate" in updates:
            task["dueDate"] = updates["dueDate"]
        if "due" in updates:
            task["due"] = updates["due"]
        self._write_payload(payload)
        before_title = _text(before.get("title") or task_id)
        after_title = _text(task.get("title") or task_id)
        if before_title != after_title:
            summary = f"Updated task '{before_title}' to '{after_title}'."
        else:
            summary = f"Updated task '{after_title}'."
        return {
            "before": before,
            "after": dict(task),
            "task_id": task_id,
            "summary": summary,
        }

    def complete_task(self, task_id: str) -> dict[str, Any]:
        return self.update_task(task_id, {"status": "completed"})

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

    def _ensure_writable(self) -> None:
        if not self.writable or not self.tasks_path:
            raise PermissionError("Task source is read-only.")

    def _read_payload(self) -> dict[str, Any]:
        if not self.tasks_path or not self.tasks_path.exists():
            return {"tasks": []}
        try:
            payload = json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Tasks file is not valid JSON.") from exc
        if isinstance(payload, list):
            return {"tasks": payload}
        if not isinstance(payload, dict):
            raise ValueError("Tasks file must contain a JSON object or list.")
        if not isinstance(payload.get("tasks"), list):
            payload["tasks"] = []
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self._ensure_writable()
        assert self.tasks_path is not None
        self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.tasks_path.with_suffix(f"{self.tasks_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.tasks_path)


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


def _raw_task_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tasks = payload.setdefault("tasks", [])
    if not isinstance(raw_tasks, list):
        raw_tasks = []
        payload["tasks"] = raw_tasks
    return raw_tasks


def _find_raw_task(payload: dict[str, Any], task_id: str) -> dict[str, Any]:
    target_id = _text(task_id)
    if not target_id:
        raise ValueError("Task id is required.")
    for task in _raw_task_records(payload):
        if not isinstance(task, dict):
            continue
        if _raw_task_id(task) == target_id:
            return task
    raise FileNotFoundError(f"Task '{target_id}' was not found.")


def _raw_task_id(raw_task: dict[str, Any]) -> str:
    return _text(raw_task.get("id") or raw_task.get("task_id") or raw_task.get("taskId"))


def _next_task_id(tasks: list[dict[str, Any]], *, title: str) -> str:
    base = _slug(title) or "task"
    used_ids = {_raw_task_id(task) for task in tasks if isinstance(task, dict)}
    if base not in used_ids:
        return base
    index = 2
    while f"{base}-{index}" in used_ids:
        index += 1
    return f"{base}-{index}"


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in re.split(r"[^a-z0-9]+", str(value or "").lower())
        if part
    )[:80].strip("-")


def _text(value: Any) -> str:
    return str(value or "").strip()
