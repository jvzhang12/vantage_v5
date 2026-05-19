from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
import json
from pathlib import Path
import re
import secrets
from typing import Any

from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.calendar import resolve_calendar_date
from vantage_v5.services.tasks import LocalTaskProvider


ARTIFACT_ACTION_STATUS_PROPOSED = "proposed"
ARTIFACT_ACTION_STATUS_ACCEPTED = "accepted"
ARTIFACT_ACTION_STATUS_REJECTED = "rejected"
ARTIFACT_ACTION_STATUS_FAILED = "failed"

CALENDAR_OPERATIONS = {
    "create_event",
    "update_event",
    "move_event",
    "replace_event",
    "cancel_event",
}
TASK_OPERATIONS = {
    "create_task",
    "update_task",
    "complete_task",
}

MUTATION_RE = re.compile(
    r"\b(?:add|create|schedule|replace|rename|change|update|move|reschedule|cancel|delete|remove)\b",
    re.IGNORECASE,
)
REPLACE_RE = re.compile(r"\breplace\s+(?P<target>.+?)\s+with\s+(?P<replacement>.+?)(?:[.!?]|\s*$)", re.IGNORECASE)
RENAME_RE = re.compile(
    r"\b(?:rename|change|update)\s+(?P<target>.+?)\s+(?:to|as|into)\s+(?P<title>.+?)(?:[.!?]|\s*$)",
    re.IGNORECASE,
)
MOVE_RE = re.compile(
    r"\b(?:move|reschedule)\s+(?P<target>.+?)\s+to\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)(?:[.!?]|\s*$)",
    re.IGNORECASE,
)
CANCEL_RE = re.compile(r"\b(?:cancel|delete|remove)\s+(?P<target>.+?)(?:[.!?]|\s*$)", re.IGNORECASE)
CREATE_RE = re.compile(
    r"\b(?:add|create|schedule)\s+(?P<title>.+?)\s+(?:at|for)\s+"
    r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)"
    r"(?:\s*(?:-|to|until)\s*(?P<end>\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?))?"
    r"(?:[.!?]|\s*$)",
    re.IGNORECASE,
)
TASK_COMPLETE_RE = re.compile(
    r"\b(?:complete|mark)\s+(?P<target>.+?)(?:\s+(?:as\s+)?(?:done|complete|completed))?(?:[.!?]|\s*$)",
    re.IGNORECASE,
)
TASK_RENAME_RE = re.compile(
    r"\b(?:rename|change|update)\s+(?:task\s+)?(?P<target>.+?)\s+(?:to|as|into)\s+(?P<title>.+?)(?:[.!?]|\s*$)",
    re.IGNORECASE,
)
TASK_MUTATION_RE = re.compile(r"\b(?:complete|mark)\b|\b(?:rename|change|update)\s+task\b", re.IGNORECASE)
TIME_PATTERN = r"\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?"
DATE_PATTERN = r"today|tomorrow|\d{4}-\d{2}-\d{2}|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
CALENDAR_CAPTURE_RE = re.compile(
    rf"^\s*(?:(?:i\s+(?:have|have got|got)|i've got|there(?:'s| is))\s+)?"
    rf"(?P<title>.+?)\s+(?:at|from)\s+(?P<start>{TIME_PATTERN})"
    rf"(?:\s*(?:-|to|until)\s*(?P<end>{TIME_PATTERN}))?\s+(?P<date>{DATE_PATTERN})\s*[.!?]?\s*$",
    re.IGNORECASE,
)
CALENDAR_CAPTURE_DATE_FIRST_RE = re.compile(
    rf"^\s*(?:my\s+)?(?P<title>.+?)\s+(?:is\s+)?(?P<date>{DATE_PATTERN})\s+"
    rf"(?:at|from)\s+(?P<start>{TIME_PATTERN})"
    rf"(?:\s*(?:-|to|until)\s*(?P<end>{TIME_PATTERN}))?\s*[.!?]?\s*$",
    re.IGNORECASE,
)
TASK_CAPTURE_RE = re.compile(
    r"^\s*(?:i\s+(?:need|have|have got|got)\s+to|i've got to|remember to|remind me to|"
    r"need to|have to|(?:add|create)\s+(?:a\s+)?task(?:\s+to)?)\s+"
    r"(?P<title>.+?)(?:[.!?]|\s*)$",
    re.IGNORECASE,
)
TASK_DATE_TRAILER_RE = re.compile(
    rf"\s+(?:(?:by|due|on)\s+)?(?P<date>{DATE_PATTERN})\s*$",
    re.IGNORECASE,
)
CALENDAR_MISSING_TIME_RE = re.compile(
    rf"^\s*(?:i\s+(?:have|have got|got)|i've got|there(?:'s| is)|my)\s+"
    rf"(?P<title>.+?)\s+(?:on\s+)?(?P<date>{DATE_PATTERN})\s*[.!?]?\s*$",
    re.IGNORECASE,
)
CAPTURE_NEGATION_RE = re.compile(
    r"\b(?:if i|i might|maybe|don't add|do not add|don't schedule|do not schedule|"
    r"no longer have|i don't have|cancelled|canceled)\b",
    re.IGNORECASE,
)
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
STOP_WORDS = {
    "the",
    "my",
    "an",
    "a",
    "event",
    "task",
    "todo",
    "to",
    "do",
    "done",
    "meeting",
    "appointment",
    "calendar",
    "today",
    "tomorrow",
    "please",
}


@dataclass(frozen=True, slots=True)
class ArtifactActionPlan:
    artifact_actions: list[dict[str, Any]]
    assistant_message: str | None = None
    error: str | None = None


class ArtifactActionStore:
    def __init__(self, actions_dir: Path) -> None:
        self.actions_dir = actions_dir

    def save(self, action: dict[str, Any]) -> dict[str, Any]:
        action_id = _safe_action_id(action.get("id"))
        if not action_id:
            raise ValueError("Artifact action id is required.")
        action["id"] = action_id
        self.actions_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(action_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(action, indent=2), encoding="utf-8")
        tmp_path.replace(path)
        return action

    def load(self, action_id: str) -> dict[str, Any]:
        path = self._path(action_id)
        if not path.exists():
            raise FileNotFoundError(f"Artifact action '{action_id}' was not found.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Artifact action '{action_id}' is invalid.")
        return payload

    def update(self, action: dict[str, Any], *, status: str | None = None) -> dict[str, Any]:
        if status:
            action["status"] = status
        action["updated_at"] = datetime.now().isoformat(timespec="seconds")
        return self.save(action)

    def _path(self, action_id: str) -> Path:
        return self.actions_dir / f"{_safe_action_id(action_id)}.json"


class ArtifactActionPlanner:
    def __init__(
        self,
        *,
        calendar_provider: LocalCalendarProvider,
        action_store: ArtifactActionStore,
        task_provider: LocalTaskProvider | None = None,
    ) -> None:
        self.calendar_provider = calendar_provider
        self.task_provider = task_provider
        self.action_store = action_store

    def plan_for_turn(
        self,
        *,
        message: str,
        visible_artifacts: list[dict[str, Any]] | None = None,
        persist: bool = True,
    ) -> ArtifactActionPlan:
        events = _visible_calendar_events(visible_artifacts or [])
        tasks = _visible_tasks(visible_artifacts or [])
        calendar_is_visible = bool(events)
        if _looks_like_artifact_mutation(message) and (calendar_is_visible or _looks_calendar_specific(message)):
            if not self.calendar_provider.writable:
                return ArtifactActionPlan(
                    artifact_actions=[],
                    assistant_message="I can see the calendar, but this calendar source is read-only. I can propose the change in chat, but I cannot apply it to this source.",
                    error="calendar_read_only",
                )

            action = self._calendar_action(message=message, events=events)
            if action.artifact_actions or action.assistant_message:
                return self.save_action_plan(action) if persist else action

        if (_looks_like_artifact_mutation(message) or _looks_like_task_mutation(message)) and (tasks or _looks_task_specific(message)):
            if not self.task_provider or not self.task_provider.writable:
                return ArtifactActionPlan(
                    artifact_actions=[],
                    assistant_message="I can see the task request, but this task source is read-only. I can propose the change in chat, but I cannot apply it to this source.",
                    error="task_read_only",
                )

            action = self._task_action(message=message, tasks=tasks)
            if action.artifact_actions or action.assistant_message:
                return self.save_action_plan(action) if persist else action

        capture_action = self._capture_action(message=message, events=events, visible_artifacts=visible_artifacts or [])
        if capture_action.artifact_actions or capture_action.assistant_message:
            return self.save_action_plan(capture_action) if persist else capture_action

        return ArtifactActionPlan(artifact_actions=[])

    def save_action_plan(self, action: ArtifactActionPlan) -> ArtifactActionPlan:
        saved_actions = [self.action_store.save(item) for item in action.artifact_actions]
        return ArtifactActionPlan(
            artifact_actions=saved_actions,
            assistant_message=_proposal_assistant_message(saved_actions[0]) if saved_actions else action.assistant_message,
            error=action.error,
        )

    def _capture_action(
        self,
        *,
        message: str,
        events: list[dict[str, Any]],
        visible_artifacts: list[dict[str, Any]],
    ) -> ArtifactActionPlan:
        if _should_skip_capture(message):
            return ArtifactActionPlan(artifact_actions=[])

        calendar_capture = _parse_calendar_capture(message, events=events)
        if calendar_capture is not None:
            if not self.calendar_provider.writable:
                return ArtifactActionPlan(
                    artifact_actions=[],
                    assistant_message="I understood that as something to add to your calendar, but this calendar source is read-only. I can keep it in chat, but I cannot apply it to this source.",
                    error="calendar_read_only",
                )
            return ArtifactActionPlan(
                artifact_actions=[
                    _calendar_create_action(
                        message=message,
                        capture=calendar_capture,
                        events=events,
                        source_refs=_source_refs_from_events(events) or _source_refs_from_visible_artifacts(visible_artifacts, kinds={"today_briefing", "calendar_day", "calendar_week"}),
                    )
                ]
            )

        task_capture = _parse_task_capture(message)
        if task_capture is not None:
            if not self.task_provider or not self.task_provider.writable:
                return ArtifactActionPlan(
                    artifact_actions=[],
                    assistant_message="I understood that as something to add to your tasks, but this task source is read-only. I can keep it in chat, but I cannot apply it to this source.",
                    error="task_read_only",
                )
            return ArtifactActionPlan(
                artifact_actions=[
                    _task_create_action(
                        message=message,
                        capture=task_capture,
                        source_refs=_source_refs_from_visible_artifacts(visible_artifacts, kinds={"today_briefing", "task_focus"}),
                    )
                ]
            )

        if _looks_like_calendar_statement_missing_time(message):
            return ArtifactActionPlan(
                artifact_actions=[],
                assistant_message="I can add that to your calendar, but I need a time first. Tell me the time or range, like 'office hours at 3 today'.",
                error="missing_calendar_time",
            )
        return ArtifactActionPlan(artifact_actions=[])

    def _calendar_action(self, *, message: str, events: list[dict[str, Any]]) -> ArtifactActionPlan:
        if match := REPLACE_RE.search(message):
            return self._targeted_update_action(
                operation="replace_event",
                message=message,
                events=events,
                target=match.group("target"),
                updates={"title": _clean_title(match.group("replacement"))},
            )
        if match := RENAME_RE.search(message):
            return self._targeted_update_action(
                operation="update_event",
                message=message,
                events=events,
                target=match.group("target"),
                updates={"title": _clean_title(match.group("title"))},
            )
        if match := MOVE_RE.search(message):
            target = match.group("target")
            found = _match_event(events, target)
            if isinstance(found, str):
                return _target_error(found, target)
            new_start = _parse_time_for_event(match.group("time"), found)
            if new_start is None:
                return ArtifactActionPlan(
                    artifact_actions=[],
                    assistant_message="I could not read the new time clearly. Please include a time like 11:00 AM.",
                    error="invalid_time",
                )
            duration = _event_end(found) - _event_start(found)
            return self._targeted_update_action(
                operation="move_event",
                message=message,
                events=events,
                target=target,
                updates={
                    "start": new_start.isoformat(),
                    "end": (new_start + duration).isoformat(),
                },
                matched_event=found,
            )
        if match := CANCEL_RE.search(message):
            target = match.group("target")
            found = _match_event(events, target)
            if isinstance(found, str):
                return _target_error(found, target)
            return ArtifactActionPlan(
                artifact_actions=[
                    _artifact_action(
                        operation="cancel_event",
                        message=message,
                        event=found,
                        updates={},
                        summary=f"Cancel {_event_title(found)}.",
                    )
                ]
            )
        if match := CREATE_RE.search(message):
            target_date = _date_from_events(events) or resolve_calendar_date("today")
            start = _parse_time_on_date(match.group("start"), target_date)
            if start is None:
                return ArtifactActionPlan(artifact_actions=[], assistant_message="I could not read the event start time clearly.", error="invalid_time")
            end = _parse_time_on_date(match.group("end"), target_date) if match.group("end") else start + timedelta(minutes=30)
            if end is None or end <= start:
                end = start + timedelta(minutes=30)
            title = _clean_title(match.group("title"))
            action = _base_action(
                artifact_kind="calendar",
                operation="create_event",
                message=message,
                summary=f"Create {title} from {_time_label(start)} to {_time_label(end)}.",
                target_refs=[],
                payload={
                    "title": title,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "calendar_id": "local",
                    "date": target_date.isoformat(),
                    "surface": _surface_context_from_events(events),
                },
                preview={
                    "before": None,
                    "after": {
                        "title": title,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "calendar_id": "local",
                    },
                },
                source_refs=_source_refs_from_events(events),
            )
            return ArtifactActionPlan(artifact_actions=[action])
        return ArtifactActionPlan(artifact_actions=[])

    def _task_action(self, *, message: str, tasks: list[dict[str, Any]]) -> ArtifactActionPlan:
        if match := TASK_COMPLETE_RE.search(message):
            target = match.group("target")
            found = _match_task(tasks, target)
            if isinstance(found, str):
                return _task_target_error(found, target)
            return ArtifactActionPlan(
                artifact_actions=[
                    _task_update_action(
                        operation="complete_task",
                        message=message,
                        task=found,
                        updates={"status": "completed"},
                        summary=f"Complete {_task_title(found)}.",
                    )
                ]
            )
        if match := TASK_RENAME_RE.search(message):
            target = match.group("target")
            found = _match_task(tasks, target)
            if isinstance(found, str):
                return _task_target_error(found, target)
            title = _clean_title(match.group("title"))
            return ArtifactActionPlan(
                artifact_actions=[
                    _task_update_action(
                        operation="update_task",
                        message=message,
                        task=found,
                        updates={"title": title},
                        summary=f"Update task {_task_title(found)} to {title}.",
                    )
                ]
            )
        return ArtifactActionPlan(artifact_actions=[])

    def _targeted_update_action(
        self,
        *,
        operation: str,
        message: str,
        events: list[dict[str, Any]],
        target: str,
        updates: dict[str, Any],
        matched_event: dict[str, Any] | None = None,
    ) -> ArtifactActionPlan:
        found = matched_event or _match_event(events, target)
        if isinstance(found, str):
            return _target_error(found, target)
        after = {**_event_record(found), **updates}
        summary = _summary_for_update(operation=operation, before=found, after=after)
        return ArtifactActionPlan(
            artifact_actions=[
                _artifact_action(
                    operation=operation,
                    message=message,
                    event=found,
                    updates=updates,
                    summary=summary,
                    after=after,
                )
            ]
        )


def execute_artifact_action(
    *,
    action: dict[str, Any],
    calendar_provider: LocalCalendarProvider,
    task_provider: LocalTaskProvider | None = None,
) -> dict[str, Any]:
    if action.get("status") != ARTIFACT_ACTION_STATUS_PROPOSED:
        raise ValueError("Only proposed artifact actions can be accepted.")
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    artifact_kind = str(action.get("artifact_kind") or "")
    operation = str(action.get("operation") or "")
    if artifact_kind == "calendar":
        if operation not in CALENDAR_OPERATIONS:
            raise ValueError("Unsupported calendar operation.")
        result = _execute_calendar_action(operation=operation, payload=payload, calendar_provider=calendar_provider)
    elif artifact_kind == "task":
        if operation not in TASK_OPERATIONS:
            raise ValueError("Unsupported task operation.")
        if task_provider is None:
            raise ValueError("Task provider is required for task artifact actions.")
        result = _execute_task_action(operation=operation, payload=payload, task_provider=task_provider)
    else:
        raise ValueError("Unsupported artifact action kind.")
    accepted = {
        **action,
        "status": ARTIFACT_ACTION_STATUS_ACCEPTED,
        "preview": {"before": result.get("before"), "after": result.get("after")},
        "result": result,
        "summary": result.get("summary") or action.get("summary") or "Artifact updated.",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return accepted


def _execute_calendar_action(
    *,
    operation: str,
    payload: dict[str, Any],
    calendar_provider: LocalCalendarProvider,
) -> dict[str, Any]:
    if operation == "create_event":
        return calendar_provider.create_event(
            title=str(payload.get("title") or "Untitled event"),
            start=_datetime_from_payload(payload.get("start")),
            end=_datetime_from_payload(payload.get("end")),
            calendar_id=str(payload.get("calendar_id") or "local"),
            location=str(payload.get("location") or ""),
            description=str(payload.get("description") or ""),
        )
    if operation == "cancel_event":
        return calendar_provider.soft_cancel_event(str(payload.get("event_id") or ""))
    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else {}
    return calendar_provider.update_event(str(payload.get("event_id") or ""), updates)


def _execute_task_action(
    *,
    operation: str,
    payload: dict[str, Any],
    task_provider: LocalTaskProvider,
) -> dict[str, Any]:
    if operation == "create_task":
        return task_provider.create_task(
            title=str(payload.get("title") or "Untitled task"),
            due_date=_date_from_payload(payload.get("due_date")),
            status=str(payload.get("status") or "open"),
            priority=str(payload.get("priority") or "normal"),
            project=str(payload.get("project") or ""),
            notes=str(payload.get("notes") or ""),
            duration_minutes=_positive_int(payload.get("duration_minutes")),
        )
    if operation == "complete_task":
        return task_provider.complete_task(str(payload.get("task_id") or ""))
    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else {}
    return task_provider.update_task(str(payload.get("task_id") or ""), updates)


def reject_artifact_action(action: dict[str, Any]) -> dict[str, Any]:
    if action.get("status") != ARTIFACT_ACTION_STATUS_PROPOSED:
        raise ValueError("Only proposed artifact actions can be rejected.")
    return {
        **action,
        "status": ARTIFACT_ACTION_STATUS_REJECTED,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def action_surface_context(action: dict[str, Any]) -> dict[str, Any]:
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    surface = payload.get("surface") if isinstance(payload.get("surface"), dict) else {}
    if surface:
        return surface
    if str(action.get("artifact_kind") or "") == "task":
        date_value = str(payload.get("due_date") or payload.get("date") or "")[:10]
        return {"kind": "task_focus", "date": date_value or resolve_calendar_date("today").isoformat()}
    date_value = str(payload.get("date") or "")[:10]
    return {"kind": "calendar_day", "date": date_value}


def action_graph_payload(action: dict[str, Any]) -> dict[str, Any]:
    artifact_kind = str(action.get("artifact_kind") or "artifact")
    return {
        "type": f"{artifact_kind}_{action.get('operation') or 'artifact_action'}",
        "action": action.get("operation"),
        "status": action.get("status"),
        "summary": action.get("summary"),
        "record_id": _first_target_id(action),
        "source": artifact_kind,
        "record_title": _first_target_title(action),
    }


def _artifact_action(
    *,
    operation: str,
    message: str,
    event: dict[str, Any],
    updates: dict[str, Any],
    summary: str,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_record = _event_record(event)
    payload = {
        "event_id": event_record.get("id"),
        "updates": updates,
        "date": str(event_record.get("start") or "")[:10],
        "surface": _surface_context(event),
    }
    return _base_action(
        artifact_kind="calendar",
        operation=operation,
        message=message,
        summary=summary,
        target_refs=[_event_ref(event_record)],
        payload=payload,
        preview={"before": event_record, "after": after or {**event_record, **updates}},
        source_refs=_source_refs_from_events([event]),
    )


def _task_update_action(
    *,
    operation: str,
    message: str,
    task: dict[str, Any],
    updates: dict[str, Any],
    summary: str,
) -> dict[str, Any]:
    task_record = _task_record(task)
    payload = {
        "task_id": task_record.get("id"),
        "updates": updates,
        "date": str(task_record.get("due_date") or "")[:10] or resolve_calendar_date("today").isoformat(),
        "surface": _task_surface_context(task),
    }
    return _base_action(
        artifact_kind="task",
        operation=operation,
        message=message,
        summary=summary,
        target_refs=[_task_ref(task_record)],
        payload=payload,
        preview={"before": task_record, "after": {**task_record, **updates}},
        source_refs=_source_refs_from_visible_task(task),
    )


def _calendar_create_action(
    *,
    message: str,
    capture: dict[str, Any],
    events: list[dict[str, Any]],
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(capture.get("title") or "Untitled event")
    start = _datetime_from_payload(capture.get("start"))
    end = _datetime_from_payload(capture.get("end"))
    target_date = start.date()
    return _base_action(
        artifact_kind="calendar",
        operation="create_event",
        message=message,
        summary=f"Create {title} from {_time_label(start)} to {_time_label(end)}.",
        target_refs=[],
        payload={
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_id": "local",
            "date": target_date.isoformat(),
            "surface": _surface_context_from_events(events) if events else {"kind": "calendar_day", "date": target_date.isoformat()},
            "capture": capture.get("capture"),
        },
        preview={
            "before": None,
            "after": {
                "title": title,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "calendar_id": "local",
            },
        },
        source_refs=source_refs,
    )


def _task_create_action(
    *,
    message: str,
    capture: dict[str, Any],
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(capture.get("title") or "Untitled task")
    due_date = str(capture.get("due_date") or "")
    date_label = f" due {due_date}" if due_date else ""
    return _base_action(
        artifact_kind="task",
        operation="create_task",
        message=message,
        summary=f"Create task '{title}'{date_label}.",
        target_refs=[],
        payload={
            "title": title,
            "due_date": due_date or None,
            "status": "open",
            "priority": "normal",
            "date": due_date or resolve_calendar_date("today").isoformat(),
            "surface": {"kind": "task_focus", "date": due_date or resolve_calendar_date("today").isoformat()},
            "capture": capture.get("capture"),
        },
        preview={
            "before": None,
            "after": {
                "title": title,
                "due_date": due_date or None,
                "status": "open",
                "priority": "normal",
            },
        },
        source_refs=source_refs,
    )


def _base_action(
    *,
    artifact_kind: str,
    operation: str,
    message: str,
    summary: str,
    target_refs: list[dict[str, Any]],
    payload: dict[str, Any],
    preview: dict[str, Any],
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": f"artifact-action-{secrets.token_hex(8)}",
        "artifact_kind": artifact_kind,
        "operation": operation,
        "status": ARTIFACT_ACTION_STATUS_PROPOSED,
        "summary": summary,
        "target_refs": target_refs,
        "payload": payload,
        "preview": preview,
        "warnings": [],
        "requires_confirmation": True,
        "source_refs": source_refs,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "origin_user_message": message,
    }


def _visible_calendar_events(visible_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for artifact in visible_artifacts:
        if not isinstance(artifact, dict):
            continue
        kind = str(artifact.get("kind") or "").strip()
        data = artifact.get("data") if isinstance(artifact.get("data"), dict) else {}
        surface = {
            "id": str(artifact.get("id") or ""),
            "kind": kind,
            "title": str(artifact.get("title") or kind or "Calendar"),
        }
        if kind in {"today_briefing", "calendar_day"}:
            calendar = data.get("calendar") if isinstance(data.get("calendar"), dict) else {}
            for event in calendar.get("events", []) if isinstance(calendar.get("events"), list) else []:
                if isinstance(event, dict):
                    events.append({**event, "_surface": {**surface, "date": str(calendar.get("date") or data.get("date") or "")}})
        elif kind == "calendar_week":
            week = data.get("calendar_week") if isinstance(data.get("calendar_week"), dict) else {}
            for day in week.get("days", []) if isinstance(week.get("days"), list) else []:
                if not isinstance(day, dict):
                    continue
                for event in day.get("events", []) if isinstance(day.get("events"), list) else []:
                    if isinstance(event, dict):
                        events.append({**event, "_surface": {**surface, "date": str(day.get("date") or "")}})
    return events


def _visible_tasks(visible_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for artifact in visible_artifacts:
        if not isinstance(artifact, dict):
            continue
        kind = str(artifact.get("kind") or "").strip()
        data = artifact.get("data") if isinstance(artifact.get("data"), dict) else {}
        surface = {
            "id": str(artifact.get("id") or ""),
            "kind": kind,
            "title": str(artifact.get("title") or kind or "Tasks"),
        }
        if kind == "today_briefing":
            task_focus = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
        elif kind == "task_focus":
            task_focus = data.get("tasks") if isinstance(data.get("tasks"), dict) else data
        else:
            task_focus = {}
        groups = task_focus.get("groups") if isinstance(task_focus.get("groups"), dict) else {}
        for group, items in groups.items():
            for task in items if isinstance(items, list) else []:
                if isinstance(task, dict):
                    tasks.append({**task, "_surface": {**surface, "date": str(task_focus.get("date") or data.get("date") or ""), "group": str(group)}})
    return tasks


def _parse_calendar_capture(message: str, *, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    match = CALENDAR_CAPTURE_RE.match(str(message or "")) or CALENDAR_CAPTURE_DATE_FIRST_RE.match(str(message or ""))
    if not match:
        return None
    title = _clean_capture_title(match.group("title"))
    if not title or title.lower().startswith("to "):
        return None
    try:
        target_date = _resolve_capture_date(match.group("date"))
    except ValueError:
        return None
    start = _parse_time_on_date(match.group("start"), target_date)
    if start is None:
        return None
    end = _parse_time_on_date(match.group("end"), target_date) if match.group("end") else start + timedelta(minutes=30)
    if end is None or end <= start:
        end = start + timedelta(minutes=30)
    return {
        "title": title,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "date": target_date.isoformat(),
        "capture": {
            "kind": "calendar_statement",
            "reason": "The user stated a concrete scheduled item with a date and time.",
            "confidence": 0.88,
            "source_message": str(message or ""),
            "parsed_fields": {
                "title": title,
                "date": target_date.isoformat(),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "visible_calendar_count": len(events),
            },
        },
    }


def _parse_task_capture(message: str) -> dict[str, Any] | None:
    match = TASK_CAPTURE_RE.match(str(message or ""))
    if not match:
        return None
    title = _clean_capture_title(match.group("title"))
    if not title:
        return None
    due_date: date | None = None
    if date_match := TASK_DATE_TRAILER_RE.search(title):
        try:
            due_date = _resolve_capture_date(date_match.group("date"))
            title = _clean_capture_title(title[: date_match.start()])
        except ValueError:
            due_date = None
    if not title:
        return None
    return {
        "title": title,
        "due_date": due_date.isoformat() if due_date else None,
        "capture": {
            "kind": "task_statement",
            "reason": "The user stated a concrete task or obligation.",
            "confidence": 0.84,
            "source_message": str(message or ""),
            "parsed_fields": {
                "title": title,
                "due_date": due_date.isoformat() if due_date else None,
            },
        },
    }


def _should_skip_capture(message: str) -> bool:
    return bool(CAPTURE_NEGATION_RE.search(str(message or "")))


def _looks_like_calendar_statement_missing_time(message: str) -> bool:
    if re.match(r"^\s*i\s+(?:need|have|have got|got)\s+to\b", str(message or ""), re.IGNORECASE):
        return False
    match = CALENDAR_MISSING_TIME_RE.match(str(message or ""))
    if not match:
        return False
    return bool(_clean_capture_title(match.group("title")))


def _resolve_capture_date(value: str | None) -> date:
    text = str(value or "today").strip().lower()
    if text in WEEKDAYS:
        today = date.today()
        delta = (WEEKDAYS[text] - today.weekday()) % 7
        if delta == 0:
            delta = 7
        return today + timedelta(days=delta)
    return resolve_calendar_date(text)


def _source_refs_from_visible_artifacts(
    visible_artifacts: list[dict[str, Any]],
    *,
    kinds: set[str],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for artifact in visible_artifacts:
        if not isinstance(artifact, dict):
            continue
        kind = str(artifact.get("kind") or "").strip()
        artifact_id = str(artifact.get("id") or "").strip()
        if not artifact_id or kind not in kinds or artifact_id in seen:
            continue
        seen.add(artifact_id)
        refs.append(
            {
                "id": artifact_id,
                "title": str(artifact.get("title") or kind),
                "kind": kind,
                "source": "visible_artifact",
                "label": str(artifact.get("title") or kind),
            }
        )
    return refs


def _looks_like_artifact_mutation(message: str) -> bool:
    return bool(MUTATION_RE.search(str(message or "")))


def _looks_like_task_mutation(message: str) -> bool:
    return bool(TASK_MUTATION_RE.search(str(message or "")))


def _looks_calendar_specific(message: str) -> bool:
    return bool(re.search(r"\b(?:calendar|event|meeting|appointment|schedule)\b", str(message or ""), re.IGNORECASE))


def _looks_task_specific(message: str) -> bool:
    return bool(re.search(r"\b(?:task|tasks|todo|to-do|checklist|homework|assignment|deadline)\b", str(message or ""), re.IGNORECASE))


def _match_event(events: list[dict[str, Any]], target: str) -> dict[str, Any] | str:
    tokens = _tokens(target)
    if not tokens:
        return "missing"
    matches: list[dict[str, Any]] = []
    target_normalized = _normalize_match_text(target)
    for event in events:
        title = _event_title(event)
        normalized_title = _normalize_match_text(title)
        title_tokens = _tokens(title)
        if target_normalized and (target_normalized in normalized_title or normalized_title in target_normalized):
            matches.append(event)
            continue
        if tokens and tokens.issubset(title_tokens):
            matches.append(event)
    if not matches:
        return "missing"
    unique: dict[str, dict[str, Any]] = {}
    for match in matches:
        unique[str(match.get("id") or match.get("title"))] = match
    matches = list(unique.values())
    if len(matches) > 1:
        return "ambiguous"
    return matches[0]


def _match_task(tasks: list[dict[str, Any]], target: str) -> dict[str, Any] | str:
    tokens = _tokens(target)
    if not tokens:
        return "missing"
    matches: list[dict[str, Any]] = []
    target_normalized = _normalize_match_text(target)
    for task in tasks:
        title = _task_title(task)
        normalized_title = _normalize_match_text(title)
        title_tokens = _tokens(title)
        if target_normalized and (target_normalized in normalized_title or normalized_title in target_normalized):
            matches.append(task)
            continue
        if tokens and tokens.issubset(title_tokens):
            matches.append(task)
    if not matches:
        return "missing"
    unique: dict[str, dict[str, Any]] = {}
    for match in matches:
        unique[str(match.get("id") or match.get("title"))] = match
    matches = list(unique.values())
    if len(matches) > 1:
        return "ambiguous"
    return matches[0]


def _target_error(error: str, target: str) -> ArtifactActionPlan:
    if error == "ambiguous":
        return ArtifactActionPlan(
            artifact_actions=[],
            assistant_message=f"I found more than one calendar event matching '{_clean_title(target)}'. Please name the exact event or time.",
            error="ambiguous_target",
        )
    return ArtifactActionPlan(
        artifact_actions=[],
        assistant_message=f"I could not find a calendar event matching '{_clean_title(target)}' in the visible calendar.",
        error="missing_target",
    )


def _task_target_error(error: str, target: str) -> ArtifactActionPlan:
    if error == "ambiguous":
        return ArtifactActionPlan(
            artifact_actions=[],
            assistant_message=f"I found more than one task matching '{_clean_title(target)}'. Please name the exact task.",
            error="ambiguous_task_target",
        )
    return ArtifactActionPlan(
        artifact_actions=[],
        assistant_message=f"I could not find a task matching '{_clean_title(target)}' in the visible task list.",
        error="missing_task_target",
    )


def _summary_for_update(*, operation: str, before: dict[str, Any], after: dict[str, Any]) -> str:
    if operation == "replace_event":
        return f"Replace {_event_title(before)} with {_event_title(after)} from {_time_label(_event_start(before))} to {_time_label(_event_end(before))}."
    if operation == "move_event":
        return f"Move {_event_title(before)} to {_time_label(_event_start(after))}."
    return f"Update {_event_title(before)} to {_event_title(after)}."


def _proposal_assistant_message(action: dict[str, Any]) -> str:
    artifact_kind = str(action.get("artifact_kind") or "artifact").strip().lower()
    summary = str(action.get("summary") or "I found an update to make.").strip()
    if artifact_kind == "calendar":
        return f"Understood. I will {summary[0].lower() + summary[1:] if summary else 'update your calendar'}\n\nI can apply this to your calendar after you confirm."
    if artifact_kind == "task":
        return f"Understood. I will {summary[0].lower() + summary[1:] if summary else 'update your tasks'}\n\nI can apply this to your tasks after you confirm."
    return f"Understood. I will {summary[0].lower() + summary[1:] if summary else 'update this artifact'}\n\nI can apply this after you confirm."


def _event_ref(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(event.get("id") or ""),
        "title": _event_title(event),
        "kind": "calendar_event",
        "source": "local_calendar",
    }


def _task_ref(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(task.get("id") or ""),
        "title": _task_title(task),
        "kind": "task",
        "source": "local_tasks",
    }


def _source_refs_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        surface = _surface_context(event)
        surface_id = str(surface.get("id") or "")
        if not surface_id or surface_id in seen:
            continue
        seen.add(surface_id)
        refs.append(
            {
                "id": surface_id,
                "title": str(surface.get("title") or "Calendar"),
                "kind": str(surface.get("kind") or "calendar"),
                "source": "visible_artifact",
                "label": str(surface.get("title") or "Calendar"),
            }
        )
    return refs


def _source_refs_from_visible_task(task: dict[str, Any]) -> list[dict[str, Any]]:
    surface = _task_surface_context(task)
    surface_id = str(surface.get("id") or "")
    if not surface_id:
        return []
    return [
        {
            "id": surface_id,
            "title": str(surface.get("title") or "Tasks"),
            "kind": str(surface.get("kind") or "task_focus"),
            "source": "visible_artifact",
            "label": str(surface.get("title") or "Tasks"),
        }
    ]


def _surface_context_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    return _surface_context(events[0]) if events else {"kind": "calendar_day", "date": resolve_calendar_date("today").isoformat()}


def _surface_context(event: dict[str, Any]) -> dict[str, Any]:
    surface = event.get("_surface") if isinstance(event.get("_surface"), dict) else {}
    if surface:
        return {
            "id": str(surface.get("id") or ""),
            "kind": str(surface.get("kind") or "calendar_day"),
            "title": str(surface.get("title") or "Calendar"),
            "date": str(surface.get("date") or str(event.get("start") or "")[:10]),
        }
    return {"kind": "calendar_day", "date": str(event.get("start") or "")[:10]}


def _event_record(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if not key.startswith("_")}


def _task_record(task: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in task.items() if not key.startswith("_")}


def _event_title(event: dict[str, Any]) -> str:
    return str(event.get("title") or event.get("summary") or "Untitled event").strip()


def _task_title(task: dict[str, Any]) -> str:
    return str(task.get("title") or task.get("name") or task.get("summary") or "Untitled task").strip()


def _task_surface_context(task: dict[str, Any]) -> dict[str, Any]:
    surface = task.get("_surface") if isinstance(task.get("_surface"), dict) else {}
    if surface:
        return {
            "id": str(surface.get("id") or ""),
            "kind": str(surface.get("kind") or "task_focus"),
            "title": str(surface.get("title") or "Tasks"),
            "date": str(surface.get("date") or str(task.get("due_date") or "")[:10]),
        }
    return {"kind": "task_focus", "date": str(task.get("due_date") or "")[:10] or resolve_calendar_date("today").isoformat()}


def _event_start(event: dict[str, Any]) -> datetime:
    return _datetime_from_payload(event.get("start"))


def _event_end(event: dict[str, Any]) -> datetime:
    return _datetime_from_payload(event.get("end"))


def _datetime_from_payload(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("A calendar datetime is required.")
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def _date_from_payload(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _parse_time_for_event(value: str, event: dict[str, Any]) -> datetime | None:
    return _parse_time_on_date(value, _event_start(event).date())


def _parse_time_on_date(value: str | None, target_date: date) -> datetime | None:
    raw = str(value or "").strip().lower().replace(".", "")
    if not raw:
        return None
    match = re.match(r"^(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>am|pm)?$", raw)
    if not match:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    meridiem = match.group("meridiem")
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if meridiem is None and 1 <= hour <= 7:
        hour += 12
    if hour > 23 or minute > 59:
        return None
    return datetime.combine(target_date, time(hour, minute))


def _date_from_events(events: list[dict[str, Any]]) -> date | None:
    for event in events:
        try:
            return _event_start(event).date()
        except ValueError:
            continue
    return None


def _time_label(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _clean_title(value: str) -> str:
    title = str(value or "").strip()
    title = re.sub(r"\s+", " ", title)
    return title.strip(" .!?")


def _clean_capture_title(value: str) -> str:
    title = _clean_title(value)
    title = re.sub(r"^(?:my|the|a|an)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+(?:on|for)$", "", title, flags=re.IGNORECASE)
    return _clean_title(title)


def _normalize_match_text(value: str) -> str:
    return " ".join(sorted(_tokens(value)))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", str(value or "").lower())
        if token and token not in STOP_WORDS
    }


def _first_target_id(action: dict[str, Any]) -> str | None:
    refs = action.get("target_refs") if isinstance(action.get("target_refs"), list) else []
    if refs and isinstance(refs[0], dict):
        return str(refs[0].get("id") or "") or None
    return None


def _first_target_title(action: dict[str, Any]) -> str | None:
    refs = action.get("target_refs") if isinstance(action.get("target_refs"), list) else []
    if refs and isinstance(refs[0], dict):
        return str(refs[0].get("title") or "") or None
    preview = action.get("preview") if isinstance(action.get("preview"), dict) else {}
    after = preview.get("after") if isinstance(preview.get("after"), dict) else {}
    return str(after.get("title") or "") or None


def _safe_action_id(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip())[:140]
