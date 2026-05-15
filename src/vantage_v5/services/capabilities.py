from __future__ import annotations

from dataclasses import dataclass
from typing import Any


POLICY_VERSION = "app-capability-v1"


@dataclass(frozen=True, slots=True)
class CapabilityResource:
    id: str
    app_id: str
    kind: str
    label: str
    description: str
    uri: str
    source: dict[str, Any]
    visible_context: str = "markdown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.app_id,
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "uri": self.uri,
            "source": dict(self.source),
            "readable": True,
            "writable": bool(self.source.get("writable")),
            "read_only": bool(self.source.get("read_only", True)),
            "visible_context": self.visible_context,
        }


@dataclass(frozen=True, slots=True)
class CapabilityTool:
    name: str
    app_id: str
    operation: str
    label: str
    description: str
    resource_ids: tuple[str, ...]
    write: bool = False
    requires_confirmation: bool = False
    destructive: bool = False
    status: str = "available"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "app_id": self.app_id,
            "operation": self.operation,
            "label": self.label,
            "description": self.description,
            "resource_ids": list(self.resource_ids),
            "write": self.write,
            "requires_confirmation": self.requires_confirmation,
            "destructive": self.destructive,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CapabilitySurface:
    kind: str
    app_id: str
    label: str
    description: str
    renderer: str
    resource_ids: tuple[str, ...]
    visible_context: str = "markdown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "app_id": self.app_id,
            "label": self.label,
            "description": self.description,
            "renderer": self.renderer,
            "resource_ids": list(self.resource_ids),
            "visible_context": self.visible_context,
        }


def build_app_capability_manifest(
    *,
    calendar_source: dict[str, Any] | None = None,
    task_source: dict[str, Any] | None = None,
    workspace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the product-facing capability contract Vantage can reason about."""
    calendar = _calendar_capability(_source(calendar_source, label="Local calendar"))
    tasks = _tasks_capability(_source(task_source, label="Local tasks"))
    whiteboard = _whiteboard_capability(workspace if isinstance(workspace, dict) else {})
    apps = [calendar, tasks, whiteboard]
    return {
        "policy_version": POLICY_VERSION,
        "apps": apps,
        "resources": _flatten(apps, "resources"),
        "tools": _flatten(apps, "tools"),
        "surfaces": _flatten(apps, "surfaces"),
        "receipt_events": _flatten(apps, "receipt_events"),
    }


def _calendar_capability(source: dict[str, Any]) -> dict[str, Any]:
    writable = bool(source.get("writable"))
    write_status = "available" if writable else "read_only"
    resources = [
        CapabilityResource(
            id="calendar.day",
            app_id="calendar",
            kind="calendar_day",
            label="Calendar day",
            description="Events and open blocks for a single day.",
            uri="calendar://day/{date}",
            source=source,
        ).to_dict(),
        CapabilityResource(
            id="calendar.week",
            app_id="calendar",
            kind="calendar_week",
            label="Calendar week",
            description="Events and open blocks across the visible week.",
            uri="calendar://week/{week_start}",
            source=source,
        ).to_dict(),
    ]
    tools = [
        CapabilityTool(
            name="calendar.read_day",
            app_id="calendar",
            operation="read_day",
            label="Read day calendar",
            description="Load the selected day calendar resource.",
            resource_ids=("calendar.day",),
        ).to_dict(),
        CapabilityTool(
            name="calendar.read_week",
            app_id="calendar",
            operation="read_week",
            label="Read week calendar",
            description="Load the selected week calendar resource.",
            resource_ids=("calendar.week",),
        ).to_dict(),
        *[
            CapabilityTool(
                name=f"calendar.{operation}",
                app_id="calendar",
                operation=operation,
                label=label,
                description=description,
                resource_ids=("calendar.day", "calendar.week"),
                write=True,
                requires_confirmation=True,
                destructive=operation == "cancel_event",
                status=write_status,
            ).to_dict()
            for operation, label, description in (
                ("create_event", "Create event", "Propose a new calendar event from an explicit request or capture."),
                ("update_event", "Update event", "Propose a safe update to a matched calendar event."),
                ("move_event", "Move event", "Propose a reschedule for a matched calendar event."),
                ("replace_event", "Replace event", "Propose replacing the title or details of a matched event."),
                ("cancel_event", "Cancel event", "Propose a soft-cancel for a matched event."),
            )
        ],
    ]
    surfaces = [
        CapabilitySurface(
            kind="calendar_day",
            app_id="calendar",
            label="Calendar",
            description="A day timeline with events, free blocks, and schedule context.",
            renderer="CalendarDaySurface",
            resource_ids=("calendar.day",),
        ).to_dict(),
        CapabilitySurface(
            kind="calendar_week",
            app_id="calendar",
            label="Calendar Week",
            description="A week timeline used when the user switches or asks about the week.",
            renderer="CalendarWeekSurface",
            resource_ids=("calendar.week",),
        ).to_dict(),
        CapabilitySurface(
            kind="today_briefing",
            app_id="calendar",
            label="Today Briefing",
            description="Composite today surface that combines calendar and task focus resources.",
            renderer="TodayBriefingSurface",
            resource_ids=("calendar.day", "tasks.focus"),
        ).to_dict(),
    ]
    return _app(
        app_id="calendar",
        label="Calendar",
        summary="Schedule, availability, time-blocking, and day/week planning.",
        invocation_policy={
            "auto_open_when": ["calendar", "schedule", "availability", "time block", "planned today", "when should I"],
            "primary_surfaces": ["calendar_day", "calendar_week", "today_briefing"],
            "visible_context_priority": "visible calendar day/week first, then provider resource",
        },
        write_behavior={
            "default": "proposal_only",
            "requires_confirmation": True,
            "commit_scope": "user_scoped_local_json" if writable else "read_only",
            "restricted_sources": ["global_env_configured_calendar"],
        },
        resources=resources,
        tools=tools,
        surfaces=surfaces,
        json_interface=_calendar_json_interface(),
    )


def _tasks_capability(source: dict[str, Any]) -> dict[str, Any]:
    writable = bool(source.get("writable"))
    write_status = "available" if writable else "read_only"
    resources = [
        CapabilityResource(
            id="tasks.focus",
            app_id="tasks",
            kind="task_focus",
            label="Task focus",
            description="Grouped tasks for must-do, good-next, deferrable, and unscheduled work.",
            uri="tasks://focus/{date}",
            source=source,
        ).to_dict()
    ]
    tools = [
        CapabilityTool(
            name="tasks.read_focus",
            app_id="tasks",
            operation="read_focus",
            label="Read task focus",
            description="Load the selected date task focus resource.",
            resource_ids=("tasks.focus",),
        ).to_dict(),
        *[
            CapabilityTool(
                name=f"tasks.{operation}",
                app_id="tasks",
                operation=operation,
                label=label,
                description=description,
                resource_ids=("tasks.focus",),
                write=True,
                requires_confirmation=True,
                status=write_status,
            ).to_dict()
            for operation, label, description in (
                ("create_task", "Create task", "Propose a task from an explicit command or captured obligation."),
                ("update_task", "Update task", "Propose a safe update to a matched task."),
                ("complete_task", "Complete task", "Propose marking a matched task complete."),
            )
        ],
    ]
    surfaces = [
        CapabilitySurface(
            kind="task_focus",
            app_id="tasks",
            label="Task Focus",
            description="A focused list of operational tasks grouped by urgency and scheduling value.",
            renderer="TaskFocusSurface",
            resource_ids=("tasks.focus",),
        ).to_dict()
    ]
    return _app(
        app_id="tasks",
        label="Tasks",
        summary="To-dos, obligations, priorities, and focus planning.",
        invocation_policy={
            "auto_open_when": ["todo", "task", "need to", "have to", "priority", "focus on"],
            "primary_surfaces": ["task_focus", "today_briefing"],
            "visible_context_priority": "visible task focus first, then provider resource",
        },
        write_behavior={
            "default": "proposal_only",
            "requires_confirmation": True,
            "commit_scope": "user_scoped_local_json" if writable else "read_only",
            "restricted_sources": ["global_env_configured_tasks"],
        },
        resources=resources,
        tools=tools,
        surfaces=surfaces,
        json_interface=_tasks_json_interface(),
    )


def _whiteboard_capability(workspace: dict[str, Any]) -> dict[str, Any]:
    has_content = bool(str(workspace.get("content") or "").strip())
    source = {
        "kind": "workspace",
        "label": workspace.get("title") or "Whiteboard",
        "configured": True,
        "read_only": False,
        "writable": True,
        "has_visible_content": has_content,
        "scope": workspace.get("scope"),
    }
    resources = [
        CapabilityResource(
            id="whiteboard.active",
            app_id="whiteboard",
            kind="whiteboard",
            label="Active whiteboard",
            description="The visible durable drafting canvas.",
            uri="whiteboard://active",
            source=source,
        ).to_dict()
    ]
    tools = [
        CapabilityTool(
            name="whiteboard.open",
            app_id="whiteboard",
            operation="open_whiteboard",
            label="Open whiteboard",
            description="Summon the drafting canvas for durable artifacts.",
            resource_ids=("whiteboard.active",),
        ).to_dict(),
        CapabilityTool(
            name="whiteboard.update_content",
            app_id="whiteboard",
            operation="update_content",
            label="Update whiteboard content",
            description="Return a full updated Markdown artifact through the ARTIFACT_UPDATE_JSON contract.",
            resource_ids=("whiteboard.active",),
            write=True,
            requires_confirmation=False,
        ).to_dict(),
        CapabilityTool(
            name="whiteboard.draft",
            app_id="whiteboard",
            operation="draft_whiteboard",
            label="Draft whiteboard",
            description="Create or update a durable draft artifact in the whiteboard.",
            resource_ids=("whiteboard.active",),
            write=True,
            requires_confirmation=False,
        ).to_dict(),
        CapabilityTool(
            name="whiteboard.save",
            app_id="whiteboard",
            operation="save_whiteboard",
            label="Save whiteboard",
            description="Persist the current whiteboard content.",
            resource_ids=("whiteboard.active",),
            write=True,
            requires_confirmation=False,
        ).to_dict(),
        CapabilityTool(
            name="whiteboard.publish",
            app_id="whiteboard",
            operation="publish_artifact",
            label="Publish artifact",
            description="Promote whiteboard content into the Library.",
            resource_ids=("whiteboard.active",),
            write=True,
            requires_confirmation=True,
        ).to_dict(),
    ]
    surfaces = [
        CapabilitySurface(
            kind="whiteboard",
            app_id="whiteboard",
            label="Whiteboard",
            description="Durable writing and planning canvas for drafts, code, outlines, and plans.",
            renderer="WhiteboardSurface",
            resource_ids=("whiteboard.active",),
        ).to_dict()
    ]
    return _app(
        app_id="whiteboard",
        label="Whiteboard",
        summary="Durable draft artifacts such as emails, essays, plans, code, and long-form notes.",
        invocation_policy={
            "auto_open_when": ["write", "draft", "essay", "email", "code", "outline", "plan"],
            "primary_surfaces": ["whiteboard"],
            "visible_context_priority": "visible whiteboard content first",
        },
        write_behavior={
            "default": "draft_surface",
            "requires_confirmation": False,
            "commit_scope": "workspace_store",
            "restricted_sources": [],
        },
        resources=resources,
        tools=tools,
        surfaces=surfaces,
        json_interface=_whiteboard_json_interface(),
    )


def _app(
    *,
    app_id: str,
    label: str,
    summary: str,
    invocation_policy: dict[str, Any],
    write_behavior: dict[str, Any],
    resources: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    surfaces: list[dict[str, Any]],
    json_interface: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": app_id,
        "label": label,
        "summary": summary,
        "invocation_policy": invocation_policy,
        "write_behavior": write_behavior,
        "json_interface": json_interface,
        "resources": resources,
        "tools": tools,
        "surfaces": surfaces,
        "receipt_events": [
            {
                "type": "capability_registered",
                "app_id": app_id,
                "label": label,
                "summary": summary,
            }
        ],
    }


def _calendar_json_interface() -> dict[str, Any]:
    return {
        "step": "artifact_mutation_compiler",
        "description": "Second-step JSON contract for converting semantic calendar edit intent into a proposed ArtifactAction. The main chat response should stay natural language.",
        "artifact_kind": "calendar",
        "operations": ["create_event", "update_event", "move_event", "replace_event", "cancel_event"],
        "output_shape": {
            "artifact_kind": "calendar",
            "operation": "create_event | update_event | move_event | replace_event | cancel_event",
            "target": "visible event title/id/time when updating an existing event",
            "payload": "validated event fields such as title, start, end, updates, or event_id",
            "requires_confirmation": True,
        },
        "commit_boundary": "Return a proposed ArtifactAction only. Calendar JSON is mutated only after Apply.",
    }


def _tasks_json_interface() -> dict[str, Any]:
    return {
        "step": "artifact_mutation_compiler",
        "description": "Second-step JSON contract for converting semantic task edit intent into a proposed ArtifactAction.",
        "artifact_kind": "task",
        "operations": ["create_task", "update_task", "complete_task"],
        "output_shape": {
            "artifact_kind": "task",
            "operation": "create_task | update_task | complete_task",
            "target": "visible task title/id when updating an existing task",
            "payload": "validated task fields such as title, due_date, updates, or task_id",
            "requires_confirmation": True,
        },
        "commit_boundary": "Return a proposed ArtifactAction only. Task JSON is mutated only after Apply.",
    }


def _whiteboard_json_interface() -> dict[str, Any]:
    return {
        "label": "ARTIFACT_UPDATE_JSON",
        "step": "artifact_mutation_compiler",
        "description": "Second-step JSON envelope for drafting or replacing whiteboard artifact content.",
        "supported_artifact_kinds": ["whiteboard"],
        "commit_boundary": "calendar and task writes still use ArtifactAction proposals and Apply confirmation",
        "schema": {
            "type": "object",
            "required": ["assistant_message", "artifact_update"],
            "properties": {
                "assistant_message": {"type": "string"},
                "artifact_update": {
                    "type": "object",
                    "required": ["artifact_kind", "operation", "content_markdown"],
                    "properties": {
                        "artifact_kind": {"type": "string", "enum": ["whiteboard"]},
                        "operation": {"type": "string", "enum": ["create", "replace_content", "update_content", "append_content"]},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "content_markdown": {"type": "string"},
                    },
                },
            },
        },
    }


def _source(value: dict[str, Any] | None, *, label: str) -> dict[str, Any]:
    source = dict(value) if isinstance(value, dict) else {}
    writable = bool(source.get("writable"))
    return {
        "kind": source.get("kind") or "local_json",
        "label": source.get("label") or label,
        "configured": bool(source.get("configured")),
        "read_only": bool(source.get("read_only", not writable)),
        "writable": writable,
        **{key: source[key] for key in ("event_count", "task_count", "has_visible_content", "scope") if key in source},
    }


def _flatten(apps: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for app in apps:
        values = app.get(key)
        if isinstance(values, list):
            items.extend([dict(item) for item in values if isinstance(item, dict)])
    return items
