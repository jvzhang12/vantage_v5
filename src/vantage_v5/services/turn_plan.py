from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TURN_PLAN_VERSION = "turn_plan.v1"


@dataclass(frozen=True, slots=True)
class TurnPlanRequest:
    message: str
    turn_id: str | None
    history_count: int
    workspace_id: str | None
    workspace_scope: str | None
    workspace_content_supplied: bool
    whiteboard_mode: str | None
    pinned_context_id: str | None
    memory_intent: str | None
    visible_artifact_ids: tuple[str, ...]
    pending_workspace_update_present: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "user_message": self.message,
            "turn_id": self.turn_id,
            "history_count": self.history_count,
            "workspace_id": self.workspace_id,
            "workspace_scope": self.workspace_scope,
            "workspace_content_supplied": self.workspace_content_supplied,
            "whiteboard_mode": self.whiteboard_mode,
            "pinned_context_id": self.pinned_context_id,
            "memory_intent": self.memory_intent,
            "visible_artifact_ids": list(self.visible_artifact_ids),
            "pending_workspace_update_present": self.pending_workspace_update_present,
        }


@dataclass(frozen=True, slots=True)
class RoutePlan:
    mode: str
    navigator_mode: str | None
    control_panel: dict[str, Any]
    reason: str | None
    confidence: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "navigator_mode": self.navigator_mode,
            "control_panel": self.control_panel,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    selected_resource_ids: tuple[str, ...]
    primary_resource_id: str | None
    selected_resources: tuple[dict[str, Any], ...]
    navigator_selection: dict[str, Any] | None
    authority: str
    openable_selected_resource_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_resource_ids": list(self.selected_resource_ids),
            "primary_resource_id": self.primary_resource_id,
            "selected_resources": [dict(resource) for resource in self.selected_resources],
            "navigator_selection": self.navigator_selection,
            "authority": self.authority,
            "openable_selected_resource_id": self.openable_selected_resource_id,
        }


@dataclass(frozen=True, slots=True)
class VisibleContextPlan:
    incoming_visible_artifact_ids: tuple[str, ...]
    response_visible_artifact_ids: tuple[str, ...]
    workspace_scope: str | None
    workspace_in_model_context: bool
    selected_resource_ids: tuple[str, ...]
    pinned_context_id: str | None
    answer_basis: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "incoming_visible_artifact_ids": list(self.incoming_visible_artifact_ids),
            "response_visible_artifact_ids": list(self.response_visible_artifact_ids),
            "workspace_scope": self.workspace_scope,
            "workspace_in_model_context": self.workspace_in_model_context,
            "selected_resource_ids": list(self.selected_resource_ids),
            "pinned_context_id": self.pinned_context_id,
            "answer_basis": self.answer_basis,
        }


@dataclass(frozen=True, slots=True)
class UiSurfaceActionPlan:
    surface: str
    mode: str
    target_resource_id: str | None
    target_resource_kind: str | None
    active_surface_id: str | None
    authority: str
    requires_explicit_signal: bool
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "mode": self.mode,
            "target_resource_id": self.target_resource_id,
            "target_resource_kind": self.target_resource_kind,
            "active_surface_id": self.active_surface_id,
            "authority": self.authority,
            "requires_explicit_signal": self.requires_explicit_signal,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class WriteIntentPlan:
    kind: str
    whiteboard_mode: str | None
    write_behavior: str
    explicit_user_intent: bool
    target_surface: str | None
    target_resource_id: str | None
    authority: str
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "whiteboard_mode": self.whiteboard_mode,
            "write_behavior": self.write_behavior,
            "explicit_user_intent": self.explicit_user_intent,
            "target_surface": self.target_surface,
            "target_resource_id": self.target_resource_id,
            "authority": self.authority,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SideEffectPolicy:
    allow_workspace_update: bool
    allow_auto_workspace_iteration_artifact: bool
    allow_auto_graph_write: bool
    allow_protocol_write: bool
    allow_artifact_actions: bool
    artifact_actions_require_confirmation: bool
    allow_calendar_task_mutation: bool
    suppress_auto_graph_writes_reason: str | None
    actual_workspace_update: bool
    actual_graph_action: bool
    actual_created_record: bool
    actual_artifact_actions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_workspace_update": self.allow_workspace_update,
            "allow_auto_workspace_iteration_artifact": self.allow_auto_workspace_iteration_artifact,
            "allow_auto_graph_write": self.allow_auto_graph_write,
            "allow_protocol_write": self.allow_protocol_write,
            "allow_artifact_actions": self.allow_artifact_actions,
            "artifact_actions_require_confirmation": self.artifact_actions_require_confirmation,
            "allow_calendar_task_mutation": self.allow_calendar_task_mutation,
            "suppress_auto_graph_writes_reason": self.suppress_auto_graph_writes_reason,
            "actual": {
                "workspace_update": self.actual_workspace_update,
                "graph_action": self.actual_graph_action,
                "created_record": self.actual_created_record,
                "artifact_actions": self.actual_artifact_actions,
            },
        }


@dataclass(frozen=True, slots=True)
class ProtocolPlan:
    applied_protocol_kinds: tuple[str, ...]
    control_panel_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied_protocol_kinds": list(self.applied_protocol_kinds),
            "control_panel_actions": list(self.control_panel_actions),
        }


@dataclass(frozen=True, slots=True)
class SemanticPlan:
    semantic_action: str | None
    policy_action_type: str | None
    should_clarify: bool
    frame_task_type: str | None
    frame_target_surface: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_action": self.semantic_action,
            "policy_action_type": self.policy_action_type,
            "should_clarify": self.should_clarify,
            "frame_task_type": self.frame_task_type,
            "frame_target_surface": self.frame_target_surface,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    service: str
    chat_whiteboard_mode: str | None
    suppress_auto_graph_writes: bool
    surface_payload_policy: str
    artifact_action_policy: str
    trace_final_response: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "chat_whiteboard_mode": self.chat_whiteboard_mode,
            "suppress_auto_graph_writes": self.suppress_auto_graph_writes,
            "surface_payload_policy": self.surface_payload_policy,
            "artifact_action_policy": self.artifact_action_policy,
            "trace_final_response": self.trace_final_response,
        }


@dataclass(frozen=True, slots=True)
class CompatibilityPlan:
    navigator_selection: bool
    surface_invocation: bool
    whiteboard_mode: str | None
    workspace_update: bool
    graph_action: bool
    created_record: bool
    artifact_actions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_paths": {
                "navigator_selection": "final_response.navigator_selection",
                "surface_invocation": "final_response.surface_invocation",
                "whiteboard_mode": "final_response.surface_invocation.resolved_whiteboard_mode",
                "workspace_update": "final_response.workspace_update",
                "graph_action": "final_response.graph_action",
                "created_record": "final_response.created_record",
                "artifact_actions": "final_response.artifact_actions",
            },
            "present": {
                "navigator_selection": self.navigator_selection,
                "surface_invocation": self.surface_invocation,
                "workspace_update": self.workspace_update,
                "graph_action": self.graph_action,
                "created_record": self.created_record,
                "artifact_actions": self.artifact_actions,
            },
            "whiteboard_mode": self.whiteboard_mode,
        }


@dataclass(frozen=True, slots=True)
class TurnPlan:
    version: str
    request: TurnPlanRequest
    route: RoutePlan
    retrieval: RetrievalPlan
    visible_context: VisibleContextPlan
    ui_surface_action: UiSurfaceActionPlan
    write_intent: WriteIntentPlan
    side_effect_policy: SideEffectPolicy
    protocols: ProtocolPlan
    semantic: SemanticPlan
    execution: ExecutionPlan
    compatibility: CompatibilityPlan

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "request": self.request.to_dict(),
            "route": self.route.to_dict(),
            "retrieval": self.retrieval.to_dict(),
            "visible_context": self.visible_context.to_dict(),
            "ui_surface_action": self.ui_surface_action.to_dict(),
            "write_intent": self.write_intent.to_dict(),
            "side_effect_policy": self.side_effect_policy.to_dict(),
            "protocols": self.protocols.to_dict(),
            "semantic": self.semantic.to_dict(),
            "execution": self.execution.to_dict(),
            "compatibility": self.compatibility.to_dict(),
            "authority": {
                "retrieval": self.retrieval.authority,
                "ui_surface_action": self.ui_surface_action.authority,
                "write_intent": self.write_intent.authority,
            },
        }


class TurnPlanBuilder:
    """Build an internal observability-only TurnPlan from finalized turn fields."""

    def build(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> TurnPlan:
        request = self._request_plan(request_payload, response_payload)
        retrieval = self._retrieval_plan(response_payload)
        visible_context = self._visible_context_plan(request_payload, response_payload, retrieval)
        ui_surface_action = self._ui_surface_action_plan(response_payload, retrieval)
        write_intent = self._write_intent_plan(response_payload, ui_surface_action)
        side_effect_policy = self._side_effect_policy(response_payload, write_intent)
        route = self._route_plan(response_payload)
        protocols = self._protocol_plan(response_payload)
        semantic = self._semantic_plan(response_payload)
        execution = self._execution_plan(response_payload, write_intent, side_effect_policy, ui_surface_action)
        compatibility = self._compatibility_plan(response_payload, write_intent)
        return TurnPlan(
            version=TURN_PLAN_VERSION,
            request=request,
            route=route,
            retrieval=retrieval,
            visible_context=visible_context,
            ui_surface_action=ui_surface_action,
            write_intent=write_intent,
            side_effect_policy=side_effect_policy,
            protocols=protocols,
            semantic=semantic,
            execution=execution,
            compatibility=compatibility,
        )

    def _request_plan(self, request_payload: dict[str, Any], response_payload: dict[str, Any]) -> TurnPlanRequest:
        history = request_payload.get("history")
        visible_artifacts = _list_of_dicts(request_payload.get("visible_artifacts"))
        pending_workspace_update = request_payload.get("pending_workspace_update")
        return TurnPlanRequest(
            message=str(request_payload.get("message") or request_payload.get("user_message") or ""),
            turn_id=_turn_id(response_payload),
            history_count=len(history) if isinstance(history, list) else 0,
            workspace_id=_optional_str(request_payload.get("workspace_id")),
            workspace_scope=_optional_str(request_payload.get("workspace_scope")),
            workspace_content_supplied=bool(request_payload.get("workspace_content_supplied")),
            whiteboard_mode=_optional_str(request_payload.get("whiteboard_mode")),
            pinned_context_id=_optional_str(request_payload.get("pinned_context_id")),
            memory_intent=_optional_str(request_payload.get("memory_intent")),
            visible_artifact_ids=tuple(_item_id(item) for item in visible_artifacts if _item_id(item)),
            pending_workspace_update_present=isinstance(pending_workspace_update, dict),
        )

    def _route_plan(self, response_payload: dict[str, Any]) -> RoutePlan:
        interpretation = _dict_or_empty(response_payload.get("turn_interpretation"))
        navigation = _dict_or_empty(interpretation.get("navigation"))
        control_panel = _dict_or_empty(interpretation.get("control_panel") or navigation.get("control_panel"))
        return RoutePlan(
            mode=str(response_payload.get("mode") or navigation.get("mode") or "chat"),
            navigator_mode=_optional_str(navigation.get("mode") or interpretation.get("mode")),
            control_panel=control_panel,
            reason=_optional_str(navigation.get("reason") or interpretation.get("reason")),
            confidence=_optional_float(navigation.get("confidence") or interpretation.get("confidence")),
        )

    def _retrieval_plan(self, response_payload: dict[str, Any]) -> RetrievalPlan:
        navigator_selection = _optional_dict(response_payload.get("navigator_selection"))
        selected_resources = tuple(
            _compact_selected_resource(item)
            for item in _list_of_dicts(response_payload.get("selected_attention_resources"))
        )
        selected_resource_ids = tuple(
            resource_id for resource_id in (_item_id(resource) for resource in selected_resources) if resource_id
        )
        primary_resource_id = _primary_resource_id(navigator_selection, selected_resource_ids)
        openable_resource_id = _openable_resource_id(primary_resource_id, selected_resources)
        authority = "none"
        if navigator_selection and (
            navigator_selection.get("selected_ids")
            or navigator_selection.get("primary_resource_id")
            or navigator_selection.get("surface_to_open")
        ):
            authority = "navigator"
        elif selected_resource_ids:
            authority = "response_payload"
        return RetrievalPlan(
            selected_resource_ids=selected_resource_ids,
            primary_resource_id=primary_resource_id,
            selected_resources=selected_resources,
            navigator_selection=navigator_selection,
            authority=authority,
            openable_selected_resource_id=openable_resource_id,
        )

    def _visible_context_plan(
        self,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        retrieval: RetrievalPlan,
    ) -> VisibleContextPlan:
        incoming_visible_artifacts = _list_of_dicts(request_payload.get("visible_artifacts"))
        response_visible_artifacts = _list_of_dicts(response_payload.get("visible_artifacts"))
        workspace = _dict_or_empty(response_payload.get("workspace"))
        workspace_scope = _optional_str(workspace.get("context_scope") or request_payload.get("workspace_scope"))
        return VisibleContextPlan(
            incoming_visible_artifact_ids=tuple(
                item_id for item_id in (_item_id(item) for item in incoming_visible_artifacts) if item_id
            ),
            response_visible_artifact_ids=tuple(
                item_id for item_id in (_item_id(item) for item in response_visible_artifacts) if item_id
            ),
            workspace_scope=workspace_scope,
            workspace_in_model_context=workspace_scope in {"visible", "pinned", "requested"},
            selected_resource_ids=retrieval.selected_resource_ids,
            pinned_context_id=_optional_str(response_payload.get("pinned_context_id") or request_payload.get("pinned_context_id")),
            answer_basis=response_payload.get("answer_basis"),
        )

    def _ui_surface_action_plan(
        self,
        response_payload: dict[str, Any],
        retrieval: RetrievalPlan,
    ) -> UiSurfaceActionPlan:
        surface_action = _optional_dict(response_payload.get("surface_action"))
        if surface_action is not None:
            target_kind = _optional_str(surface_action.get("target_kind") or surface_action.get("target"))
            return UiSurfaceActionPlan(
                surface=target_kind or "current",
                mode="close" if surface_action.get("status") != "no_visible_surface" else "close_noop",
                target_resource_id=_optional_str(surface_action.get("target_id")),
                target_resource_kind=target_kind,
                active_surface_id=_optional_str(response_payload.get("active_surface_id")),
                authority="surface_action",
                requires_explicit_signal=True,
                reason=_optional_str(surface_action.get("reason")),
            )
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        navigator_selection = retrieval.navigator_selection or {}
        nav_surface = _optional_str(navigator_selection.get("surface_to_open"))
        primary_surface = _optional_str(invocation.get("primary_surface"))
        write_behavior = _normalized_write_behavior(invocation)
        if nav_surface:
            surface = nav_surface
        elif primary_surface and primary_surface != "chat":
            surface = primary_surface
        else:
            surface = "none"

        if write_behavior == "open_only":
            mode = "open_only"
        elif write_behavior == "read_only":
            mode = "read_only"
        elif write_behavior == "draft_only":
            mode = "draft"
        elif write_behavior == "proposal_only":
            mode = "proposal_only"
        elif write_behavior == "artifact_branching":
            mode = "artifact_branching"
        elif surface != "none":
            mode = "foreground_existing"
        else:
            mode = "none"

        authority = _surface_authority(invocation, navigator_selection, surface)
        target_resource_id = (
            retrieval.primary_resource_id
            if surface == "whiteboard"
            else _optional_str(response_payload.get("active_surface_id"))
        )
        target_resource_kind = _resource_kind_for_id(target_resource_id, retrieval.selected_resources)
        return UiSurfaceActionPlan(
            surface=surface,
            mode=mode,
            target_resource_id=target_resource_id,
            target_resource_kind=target_resource_kind,
            active_surface_id=_optional_str(response_payload.get("active_surface_id")),
            authority=authority,
            requires_explicit_signal=surface == "whiteboard",
            reason=_optional_str(invocation.get("reason") or navigator_selection.get("reason")),
        )

    def _write_intent_plan(
        self,
        response_payload: dict[str, Any],
        ui_surface_action: UiSurfaceActionPlan,
    ) -> WriteIntentPlan:
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        interpretation = _dict_or_empty(response_payload.get("turn_interpretation"))
        write_behavior = _normalized_write_behavior(invocation)
        whiteboard_mode = _optional_str(
            invocation.get("resolved_whiteboard_mode")
            or invocation.get("whiteboard_mode")
            or interpretation.get("resolved_whiteboard_mode")
        )
        workspace_update = _optional_dict(response_payload.get("workspace_update"))
        graph_action = _optional_dict(response_payload.get("graph_action"))
        artifact_actions = _list_of_dicts(response_payload.get("artifact_actions"))
        if write_behavior == "artifact_branching":
            kind = "scenario_branching"
        elif write_behavior == "open_only":
            kind = "ui_open_only"
        elif whiteboard_mode == "draft" or write_behavior == "draft_only":
            kind = "whiteboard_draft"
        elif whiteboard_mode == "offer" or _workspace_update_status(workspace_update) == "offered":
            kind = "whiteboard_offer"
        elif graph_action:
            kind = "graph_write"
        elif artifact_actions:
            kind = "artifact_action_proposal"
        else:
            kind = "none"
        explicit_user_intent = bool(
            interpretation.get("explicit_whiteboard_draft_request")
            or _control_panel_has_write_action(interpretation)
            or kind in {"graph_write", "scenario_branching", "artifact_action_proposal"}
        )
        return WriteIntentPlan(
            kind=kind,
            whiteboard_mode=whiteboard_mode,
            write_behavior=write_behavior,
            explicit_user_intent=explicit_user_intent,
            target_surface=_optional_str(invocation.get("primary_surface")),
            target_resource_id=ui_surface_action.target_resource_id,
            authority=_optional_str(invocation.get("trigger") or invocation.get("selection_authority")) or "response_payload",
            reason=_optional_str(invocation.get("reason")),
        )

    def _side_effect_policy(
        self,
        response_payload: dict[str, Any],
        write_intent: WriteIntentPlan,
    ) -> SideEffectPolicy:
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        surface_action = _optional_dict(response_payload.get("surface_action"))
        intent = _optional_str(invocation.get("intent"))
        artifact_qna = intent in {"current_artifact_followup", "selected_material_question"}
        open_only = write_intent.write_behavior == "open_only"
        suppress_reason = None
        if surface_action is not None:
            suppress_reason = "close_visible_surface"
        elif open_only:
            suppress_reason = "open_only_ui_handoff"
        elif artifact_qna:
            suppress_reason = "artifact_qna_chat_first"

        workspace_update = _optional_dict(response_payload.get("workspace_update"))
        graph_action = _optional_dict(response_payload.get("graph_action"))
        created_record = _optional_dict(response_payload.get("created_record"))
        artifact_actions = _list_of_dicts(response_payload.get("artifact_actions"))
        suppressed = suppress_reason is not None
        allow_workspace_update = not suppressed and (
            write_intent.whiteboard_mode in {"offer", "draft"}
            or write_intent.write_behavior == "draft_only"
            or workspace_update is not None
        )
        allow_artifact_actions = not suppressed and (
            write_intent.write_behavior == "proposal_only" or bool(artifact_actions)
        )
        return SideEffectPolicy(
            allow_workspace_update=allow_workspace_update,
            allow_auto_workspace_iteration_artifact=not suppressed and write_intent.write_behavior == "draft_only",
            allow_auto_graph_write=not suppressed,
            allow_protocol_write=not suppressed,
            allow_artifact_actions=allow_artifact_actions,
            artifact_actions_require_confirmation=True,
            allow_calendar_task_mutation=False,
            suppress_auto_graph_writes_reason=suppress_reason,
            actual_workspace_update=workspace_update is not None,
            actual_graph_action=graph_action is not None,
            actual_created_record=created_record is not None,
            actual_artifact_actions=len(artifact_actions),
        )

    def _protocol_plan(self, response_payload: dict[str, Any]) -> ProtocolPlan:
        interpretation = _dict_or_empty(response_payload.get("turn_interpretation"))
        control_panel = _dict_or_empty(interpretation.get("control_panel"))
        applied = response_payload.get("applied_protocol_kinds")
        if not isinstance(applied, list):
            applied = control_panel.get("applied_protocol_kinds")
        actions = _list_of_dicts(control_panel.get("actions"))
        return ProtocolPlan(
            applied_protocol_kinds=tuple(str(item) for item in (applied or []) if str(item).strip()),
            control_panel_actions=tuple(
                str(action.get("type") or action.get("action") or "").strip()
                for action in actions
                if str(action.get("type") or action.get("action") or "").strip()
            ),
        )

    def _semantic_plan(self, response_payload: dict[str, Any]) -> SemanticPlan:
        semantic_frame = _dict_or_empty(response_payload.get("semantic_frame"))
        semantic_policy = _dict_or_empty(response_payload.get("semantic_policy"))
        return SemanticPlan(
            semantic_action=_optional_str(semantic_policy.get("semantic_action")),
            policy_action_type=_optional_str(semantic_policy.get("action_type")),
            should_clarify=bool(semantic_policy.get("should_clarify") or semantic_policy.get("needs_clarification")),
            frame_task_type=_optional_str(semantic_frame.get("task_type")),
            frame_target_surface=_optional_str(semantic_frame.get("target_surface")),
        )

    def _execution_plan(
        self,
        response_payload: dict[str, Any],
        write_intent: WriteIntentPlan,
        side_effect_policy: SideEffectPolicy,
        ui_surface_action: UiSurfaceActionPlan,
    ) -> ExecutionPlan:
        mode = str(response_payload.get("mode") or "chat")
        service = "scenario_lab" if mode == "scenario_lab" else "chat"
        if write_intent.kind in {"save_whiteboard", "publish_artifact"}:
            service = "local_semantic_action"
        surface_payload_policy = (
            "build_operational_payload"
            if ui_surface_action.surface in {"calendar_day", "calendar_week", "task_focus", "today_briefing"}
            else "none"
        )
        return ExecutionPlan(
            service=service,
            chat_whiteboard_mode=write_intent.whiteboard_mode,
            suppress_auto_graph_writes=not side_effect_policy.allow_auto_graph_write,
            surface_payload_policy=surface_payload_policy,
            artifact_action_policy="compile_proposals" if side_effect_policy.allow_artifact_actions else "disabled",
            trace_final_response=True,
        )

    def _compatibility_plan(
        self,
        response_payload: dict[str, Any],
        write_intent: WriteIntentPlan,
    ) -> CompatibilityPlan:
        return CompatibilityPlan(
            navigator_selection=isinstance(response_payload.get("navigator_selection"), dict),
            surface_invocation=isinstance(response_payload.get("surface_invocation"), dict),
            whiteboard_mode=write_intent.whiteboard_mode,
            workspace_update=isinstance(response_payload.get("workspace_update"), dict),
            graph_action=isinstance(response_payload.get("graph_action"), dict),
            created_record=isinstance(response_payload.get("created_record"), dict),
            artifact_actions=len(_list_of_dicts(response_payload.get("artifact_actions"))),
        )


def turn_plan_trace_payload(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    return TurnPlanBuilder().build(
        request_payload=request_payload,
        response_payload=response_payload,
    ).to_dict()


def _turn_id(response_payload: dict[str, Any]) -> str | None:
    memory_trace = response_payload.get("memory_trace_record")
    if isinstance(memory_trace, dict):
        return _optional_str(memory_trace.get("id"))
    return None


def _primary_resource_id(navigator_selection: dict[str, Any] | None, selected_resource_ids: tuple[str, ...]) -> str | None:
    if navigator_selection:
        primary = _optional_str(navigator_selection.get("primary_resource_id"))
        if primary:
            return primary
        selected_ids = navigator_selection.get("selected_ids")
        if isinstance(selected_ids, list):
            for item in selected_ids:
                value = _optional_str(item)
                if value:
                    return value
    return selected_resource_ids[0] if selected_resource_ids else None


def _openable_resource_id(primary_resource_id: str | None, selected_resources: tuple[dict[str, Any], ...]) -> str | None:
    if primary_resource_id and _is_openable_resource_id(primary_resource_id):
        return primary_resource_id
    for resource in selected_resources:
        resource_id = _item_id(resource)
        if resource_id and _is_openable_resource_id(resource_id):
            return resource_id
    return None


def _is_openable_resource_id(value: str) -> bool:
    return value.startswith(("artifact:", "workspace:", "whiteboard:"))


def _compact_selected_resource(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content")
    return {
        "resource_id": _item_id(item),
        "id": _optional_str(item.get("id")),
        "title": _optional_str(item.get("title")),
        "kind": _optional_str(item.get("kind")),
        "source": _optional_str(item.get("source")),
        "suggested_surface": _optional_str(item.get("suggested_surface")),
        "scope": _optional_str(item.get("scope")),
        "durability": _optional_str(item.get("durability")),
        "is_canonical": item.get("is_canonical") if isinstance(item.get("is_canonical"), bool) else None,
        "content_present": bool(str(content or "").strip()),
    }


def _surface_authority(
    invocation: dict[str, Any],
    navigator_selection: dict[str, Any],
    surface: str,
) -> str:
    if navigator_selection.get("surface_to_open"):
        return "navigator_selection"
    selection_authority = _optional_str(invocation.get("selection_authority"))
    if selection_authority:
        return selection_authority
    trigger = _optional_str(invocation.get("trigger"))
    if trigger and surface != "none":
        return trigger
    return "none"


def _resource_kind_for_id(resource_id: str | None, selected_resources: tuple[dict[str, Any], ...]) -> str | None:
    if resource_id:
        for resource in selected_resources:
            if _item_id(resource) == resource_id:
                return _optional_str(resource.get("kind") or resource.get("suggested_surface"))
        if ":" in resource_id:
            return resource_id.split(":", 1)[0]
    return None


def _control_panel_has_write_action(interpretation: dict[str, Any]) -> bool:
    control_panel = _dict_or_empty(interpretation.get("control_panel"))
    for action in _list_of_dicts(control_panel.get("actions")):
        action_type = str(action.get("type") or action.get("action") or "").strip()
        if action_type in {"draft_whiteboard", "save_whiteboard", "publish_artifact"}:
            return True
    return False


def _workspace_update_status(workspace_update: dict[str, Any] | None) -> str | None:
    if not workspace_update:
        return None
    return _optional_str(workspace_update.get("status") or workspace_update.get("type"))


def _normalized_write_behavior(invocation: dict[str, Any]) -> str:
    return str(invocation.get("write_behavior") or "none").strip().lower() or "none"


def _item_id(item: dict[str, Any]) -> str | None:
    return _optional_str(item.get("resource_id") or item.get("id"))


def _optional_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
