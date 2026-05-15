from __future__ import annotations

from vantage_v5.services.capabilities import build_app_capability_manifest


def test_capability_manifest_registers_calendar_tasks_and_whiteboard() -> None:
    manifest = build_app_capability_manifest(
        calendar_source={"kind": "local_json", "label": "Local calendar", "configured": True, "read_only": False, "writable": True},
        task_source={"kind": "local_json", "label": "Local tasks", "configured": True, "read_only": False, "writable": True},
        workspace={"title": "Whiteboard", "content": "Draft body", "scope": "durable"},
    )

    assert manifest["policy_version"] == "app-capability-v1"
    assert [app["id"] for app in manifest["apps"]] == ["calendar", "tasks", "whiteboard"]
    assert _app(manifest, "calendar")["json_interface"]["step"] == "artifact_mutation_compiler"
    assert _app(manifest, "whiteboard")["json_interface"]["label"] == "ARTIFACT_UPDATE_JSON"
    assert {resource["id"] for resource in manifest["resources"]} >= {"calendar.day", "calendar.week", "tasks.focus", "whiteboard.active"}
    assert {surface["kind"] for surface in manifest["surfaces"]} >= {"calendar_day", "calendar_week", "task_focus", "whiteboard", "today_briefing"}
    assert _tool(manifest, "calendar.create_event")["requires_confirmation"] is True
    assert _tool(manifest, "tasks.create_task")["status"] == "available"
    assert _tool(manifest, "whiteboard.update_content")["requires_confirmation"] is False
    assert _tool(manifest, "whiteboard.draft")["write"] is True


def test_capability_manifest_marks_global_sources_read_only() -> None:
    manifest = build_app_capability_manifest(
        calendar_source={"kind": "local_json", "label": "Global calendar", "configured": True, "read_only": True},
        task_source={"kind": "local_json", "label": "Global tasks", "configured": True, "read_only": True},
    )

    assert _tool(manifest, "calendar.replace_event")["status"] == "read_only"
    assert _tool(manifest, "tasks.complete_task")["status"] == "read_only"
    assert _resource(manifest, "calendar.day")["read_only"] is True
    assert _resource(manifest, "tasks.focus")["writable"] is False


def _tool(manifest: dict, name: str) -> dict:
    return next(tool for tool in manifest["tools"] if tool["name"] == name)


def _app(manifest: dict, app_id: str) -> dict:
    return next(app for app in manifest["apps"] if app["id"] == app_id)


def _resource(manifest: dict, resource_id: str) -> dict:
    return next(resource for resource in manifest["resources"] if resource["id"] == resource_id)
