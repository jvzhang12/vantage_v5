from __future__ import annotations

import json
import logging
import re
from typing import Any

from vantage_v5.services.artifact_actions import ArtifactActionPlan
from vantage_v5.services.artifact_actions import ArtifactActionPlanner
from vantage_v5.services.model_client import create_model_client
from vantage_v5.services.model_client import ModelClientConfig


logger = logging.getLogger(__name__)


MUTATION_HINT_RE = re.compile(
    r"\b(?:add|create|schedule|replace|rename|change|update|move|reschedule|cancel|delete|remove|complete|mark)\b",
    re.IGNORECASE,
)
CALENDAR_HINT_RE = re.compile(r"\b(?:calendar|schedule|event|meeting|appointment|office hours|class|lecture)\b", re.IGNORECASE)
TASK_HINT_RE = re.compile(r"\b(?:task|todo|to-do|homework|assignment|need to|have to|finish|complete)\b", re.IGNORECASE)
CALENDAR_CAPTURE_HINT_RE = re.compile(
    r"\b(?:i\s+(?:have|have got|got)|i've got|there(?:'s| is)|my)\b.+\b(?:at|from)\b.+\b(?:today|tomorrow|\d{4}-\d{2}-\d{2}|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
TASK_CAPTURE_HINT_RE = re.compile(r"\b(?:i\s+(?:need|have|have got|got)\s+to|i've got to|remember to|remind me to|need to|have to)\b", re.IGNORECASE)


class ArtifactMutationCompiler:
    """Second-step compiler from semantic action text into Vantage ArtifactAction JSON."""

    def __init__(
        self,
        *,
        planner: ArtifactActionPlanner,
        app_capabilities: dict[str, Any] | None = None,
        model: str,
        model_client_config: ModelClientConfig | None = None,
    ) -> None:
        self.planner = planner
        self.app_capabilities = app_capabilities if isinstance(app_capabilities, dict) else {}
        self.model = model
        self.client = create_model_client(model_client_config)

    def compile_for_turn(
        self,
        *,
        user_message: str,
        semantic_action: str,
        visible_artifacts: list[dict[str, Any]] | None = None,
        persist: bool = True,
    ) -> ArtifactActionPlan:
        if not _should_compile(user_message=user_message, semantic_action=semantic_action, visible_artifacts=visible_artifacts or []):
            return ArtifactActionPlan(artifact_actions=[])
        interface = app_json_interface_for_turn(
            self.app_capabilities,
            user_message=user_message,
            semantic_action=semantic_action,
            visible_artifacts=visible_artifacts or [],
        )
        normalized = self._normalize_with_model(
            user_message=user_message,
            semantic_action=semantic_action,
            visible_artifacts=visible_artifacts or [],
            app_interface=interface,
        )
        command = normalized or semantic_action or user_message
        source = "model_normalized" if normalized is not None else "deterministic_fallback"
        plan = self.planner.plan_for_turn(message=command, visible_artifacts=visible_artifacts, persist=False)
        repairs: list[dict[str, Any]] = []
        if plan.artifact_actions and command != user_message and _task_create_plan_missing_due_date(plan):
            raw_plan = self.planner.plan_for_turn(message=user_message, visible_artifacts=visible_artifacts, persist=False)
            if _task_create_plan_has_due_date(raw_plan):
                plan = _repair_task_create_due_dates(plan, raw_plan)
                repairs.append(
                    {
                        "kind": "task_due_date",
                        "source": "deterministic_fallback",
                        "compiler_input": user_message,
                    }
                )
        if not plan.artifact_actions and command != user_message:
            source = "deterministic_fallback"
            command = user_message
            plan = self.planner.plan_for_turn(message=user_message, visible_artifacts=visible_artifacts, persist=False)
            repairs = []
        annotated = _annotate_plan(
            plan,
            semantic_action=semantic_action,
            compiler_input=command,
            app_interface=interface,
            source=source,
            repairs=repairs,
        )
        return self.persist_plan(annotated) if persist else annotated

    def persist_plan(self, plan: ArtifactActionPlan) -> ArtifactActionPlan:
        return self.planner.save_action_plan(plan)

    def _normalize_with_model(
        self,
        *,
        user_message: str,
        semantic_action: str,
        visible_artifacts: list[dict[str, Any]],
        app_interface: dict[str, Any],
    ) -> str | None:
        if self.client is None:
            return None
        try:
            response = self.client.responses.create(
                model=self.model,
                store=False,
                instructions=(
                    "You are Vantage's artifact mutation compiler. "
                    "This is the second step after the main assistant response. "
                    "Convert the user's request and assistant semantic understanding into one concise natural-language mutation command that conforms to the relevant app JSON interface. "
                    "Do not answer the user. Do not commit writes. Return only JSON."
                ),
                input=json.dumps(
                    {
                        "user_message": user_message,
                        "semantic_action": semantic_action,
                        "visible_artifacts": visible_artifacts,
                        "app_interface": app_interface,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "vantage_artifact_mutation_compiler",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "should_mutate": {"type": "boolean"},
                                "artifact_kind": {"type": "string", "enum": ["calendar", "task", "whiteboard", "none"]},
                                "normalized_action": {"type": ["string", "null"]},
                                "reason": {"type": "string"},
                            },
                            "required": ["should_mutate", "artifact_kind", "normalized_action", "reason"],
                        },
                    }
                },
            )
            payload = json.loads(response.output_text)
        except Exception:
            logger.exception("Artifact mutation compiler model call failed; using deterministic compiler fallback.")
            return None
        if not isinstance(payload, dict) or not payload.get("should_mutate"):
            return None
        normalized = str(payload.get("normalized_action") or "").strip()
        return normalized or None


def app_json_interface_for_turn(
    app_capabilities: dict[str, Any] | None,
    *,
    user_message: str,
    semantic_action: str,
    visible_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = app_capabilities if isinstance(app_capabilities, dict) else {}
    app_ids = _relevant_app_ids(
        user_message=user_message,
        semantic_action=semantic_action,
        visible_artifacts=visible_artifacts,
    )
    apps = [
        _compiler_app_payload(app)
        for app in manifest.get("apps", [])
        if isinstance(app, dict) and str(app.get("id") or "") in app_ids
    ]
    resources = [
        _compiler_resource_payload(resource)
        for resource in manifest.get("resources", [])
        if isinstance(resource, dict) and str(resource.get("app_id") or "") in app_ids
    ]
    tools = [
        _compiler_tool_payload(tool)
        for tool in manifest.get("tools", [])
        if isinstance(tool, dict) and str(tool.get("app_id") or "") in app_ids
    ]
    return {
        "policy_version": manifest.get("policy_version"),
        "step": "artifact_mutation_compiler",
        "apps": apps,
        "resources": resources,
        "tools": tools,
    }


def _annotate_plan(
    plan: ArtifactActionPlan,
    *,
    semantic_action: str,
    compiler_input: str,
    app_interface: dict[str, Any],
    source: str,
    repairs: list[dict[str, Any]] | None = None,
) -> ArtifactActionPlan:
    if not plan.artifact_actions:
        return plan
    normalized_by_model = source == "model_normalized"
    contract_refs = [
        f"{app.get('id')}.json_interface"
        for app in app_interface.get("apps", [])
        if isinstance(app, dict) and app.get("json_interface")
    ]
    annotated = []
    for action in plan.artifact_actions:
        annotated.append(
            {
                **action,
                "compiler": {
                    "pipeline": "semantic_then_json_contract",
                    "step": "artifact_mutation_compiler",
                    "source": source,
                    "semantic_action": semantic_action,
                    "compiler_input": compiler_input,
                    "model_normalized": normalized_by_model,
                    "contract_refs": contract_refs,
                    "app_interface": app_interface,
                    **({"repairs": repairs} if repairs else {}),
                },
            }
        )
    return ArtifactActionPlan(artifact_actions=annotated, assistant_message=plan.assistant_message, error=plan.error)


def _task_create_plan_missing_due_date(plan: ArtifactActionPlan) -> bool:
    return any(_is_task_create_action_missing_due_date(action) for action in plan.artifact_actions)


def _task_create_plan_has_due_date(plan: ArtifactActionPlan) -> bool:
    return any(_is_task_create_action_with_due_date(action) for action in plan.artifact_actions)


def _is_task_create_action_missing_due_date(action: dict[str, Any]) -> bool:
    if str(action.get("artifact_kind") or "") != "task" or str(action.get("operation") or "") != "create_task":
        return False
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    return not str(payload.get("due_date") or "").strip()


def _is_task_create_action_with_due_date(action: dict[str, Any]) -> bool:
    if str(action.get("artifact_kind") or "") != "task" or str(action.get("operation") or "") != "create_task":
        return False
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    return bool(str(payload.get("due_date") or "").strip())


def _repair_task_create_due_dates(plan: ArtifactActionPlan, raw_plan: ArtifactActionPlan) -> ArtifactActionPlan:
    raw_payload = _first_task_create_payload_with_due_date(raw_plan)
    if raw_payload is None:
        return plan
    due_date = str(raw_payload.get("due_date") or "").strip()
    if not due_date:
        return plan
    repaired_actions = []
    for action in plan.artifact_actions:
        if not _is_task_create_action_missing_due_date(action):
            repaired_actions.append(action)
            continue
        payload = dict(action.get("payload") if isinstance(action.get("payload"), dict) else {})
        raw_surface = raw_payload.get("surface") if isinstance(raw_payload.get("surface"), dict) else {}
        surface = dict(payload.get("surface") if isinstance(payload.get("surface"), dict) else {})
        surface["date"] = str(raw_surface.get("date") or due_date)
        payload["due_date"] = due_date
        payload["date"] = str(raw_payload.get("date") or due_date)
        payload["surface"] = surface
        preview = dict(action.get("preview") if isinstance(action.get("preview"), dict) else {})
        after = dict(preview.get("after") if isinstance(preview.get("after"), dict) else {})
        after["due_date"] = due_date
        preview["after"] = after
        title = str(payload.get("title") or "Untitled task")
        repaired_actions.append(
            {
                **action,
                "summary": f"Create task '{title}' due {due_date}.",
                "payload": payload,
                "preview": preview,
            }
        )
    return ArtifactActionPlan(artifact_actions=repaired_actions, assistant_message=plan.assistant_message, error=plan.error)


def _first_task_create_payload_with_due_date(plan: ArtifactActionPlan) -> dict[str, Any] | None:
    for action in plan.artifact_actions:
        if not _is_task_create_action_with_due_date(action):
            continue
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return payload
    return None


def _should_compile(*, user_message: str, semantic_action: str, visible_artifacts: list[dict[str, Any]]) -> bool:
    text = f"{user_message}\n{semantic_action}".strip()
    if MUTATION_HINT_RE.search(text):
        return True
    if CALENDAR_CAPTURE_HINT_RE.search(text) or TASK_CAPTURE_HINT_RE.search(text):
        return True
    if any(str(artifact.get("kind") or "") in {"calendar_day", "calendar_week", "today_briefing", "task_focus"} for artifact in visible_artifacts):
        return bool(CALENDAR_HINT_RE.search(text) or TASK_HINT_RE.search(text))
    return False


def _relevant_app_ids(*, user_message: str, semantic_action: str, visible_artifacts: list[dict[str, Any]]) -> set[str]:
    text = f"{user_message}\n{semantic_action}"
    app_ids: set[str] = set()
    kinds = {str(artifact.get("kind") or "") for artifact in visible_artifacts if isinstance(artifact, dict)}
    if CALENDAR_HINT_RE.search(text) or kinds.intersection({"calendar_day", "calendar_week", "today_briefing"}):
        app_ids.add("calendar")
    if TASK_HINT_RE.search(text) or kinds.intersection({"task_focus", "today_briefing"}):
        app_ids.add("tasks")
    if not app_ids:
        app_ids.add("calendar")
        app_ids.add("tasks")
    return app_ids


def _compiler_app_payload(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": app.get("id"),
        "label": app.get("label"),
        "summary": app.get("summary"),
        "write_behavior": app.get("write_behavior") if isinstance(app.get("write_behavior"), dict) else {},
        "json_interface": app.get("json_interface") if isinstance(app.get("json_interface"), dict) else {},
    }


def _compiler_resource_payload(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": resource.get("id"),
        "kind": resource.get("kind"),
        "label": resource.get("label"),
        "writable": bool(resource.get("writable")),
        "read_only": bool(resource.get("read_only", not bool(resource.get("writable")))),
    }


def _compiler_tool_payload(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool.get("name"),
        "operation": tool.get("operation"),
        "label": tool.get("label"),
        "write": bool(tool.get("write")),
        "requires_confirmation": bool(tool.get("requires_confirmation")),
        "status": tool.get("status"),
    }
