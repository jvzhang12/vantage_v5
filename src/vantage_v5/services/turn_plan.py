from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TURN_PLAN_VERSION = "turn_plan.v1"
NO_WRITE_LEDGER_CATEGORIES = frozenset({"none", "open_only_no_write"})
NO_WRITE_EXECUTION_CATEGORIES = {
    "open_only_ui_handoff": "open_only_no_write",
    "close_visible_surface": "close_visible_surface",
    "preserve_visible_surface": "preserve_visible_surface",
    "artifact_qna_chat_first": "visible_selected_artifact_qna",
}
_CONCEPT_WRITE_ACTIONS = frozenset(
    {
        "learn",
        "conceptualize",
        "create_concept",
        "create_revision",
        "revise_concept",
        "concept_write",
        "save_concept",
        "upsert_concept",
    }
)


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
class TurnPlanSurfaceAuthority:
    """Authoritative internal surface-action view derived from TurnPlan fields."""

    ui_surface_action: UiSurfaceActionPlan
    write_intent: WriteIntentPlan
    side_effect_policy: SideEffectPolicy
    surface_invocation: dict[str, Any]
    surface_action: dict[str, Any] | None

    @property
    def is_close(self) -> bool:
        return self.ui_surface_action.mode in {"close", "close_noop"}

    @property
    def is_preserve(self) -> bool:
        return self.ui_surface_action.mode == "preserve"

    @property
    def is_whiteboard_open_only(self) -> bool:
        return self.ui_surface_action.surface == "whiteboard" and self.ui_surface_action.mode == "open_only"

    @property
    def no_write_reason(self) -> str | None:
        return self.side_effect_policy.suppress_auto_graph_writes_reason

    @property
    def writes_forbidden(self) -> bool:
        return self.no_write_reason is not None

    @property
    def enforced_no_write_categories(self) -> tuple[str, ...]:
        reason = self.no_write_reason
        if reason is None:
            return ()
        category = NO_WRITE_EXECUTION_CATEGORIES.get(reason)
        return (category,) if category else (reason,)

    @property
    def suppress_auto_graph_writes(self) -> bool:
        return self.writes_forbidden

    @property
    def blocks_artifact_actions(self) -> bool:
        return self.writes_forbidden

    @property
    def blocks_protocol_writes(self) -> bool:
        return self.no_write_reason in {
            "open_only_ui_handoff",
            "close_visible_surface",
            "preserve_visible_surface",
        }

    @property
    def blocks_local_semantic_writes(self) -> bool:
        return self.blocks_protocol_writes

    @property
    def surface_payload_policy(self) -> str:
        return (
            "build_operational_payload"
            if self.ui_surface_action.surface in {"calendar_day", "calendar_week", "task_focus", "today_briefing"}
            else "none"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ui_surface_action": self.ui_surface_action.to_dict(),
            "write_intent": self.write_intent.to_dict(),
            "side_effect_policy": self.side_effect_policy.to_dict(),
            "surface_invocation": dict(self.surface_invocation),
            "surface_action": dict(self.surface_action) if self.surface_action else None,
            "execution": {
                "writes_forbidden": self.writes_forbidden,
                "no_write_reason": self.no_write_reason,
                "enforced_no_write_categories": list(self.enforced_no_write_categories),
                "suppress_auto_graph_writes": self.suppress_auto_graph_writes,
                "artifact_action_policy": "disabled" if self.blocks_artifact_actions else "legacy_postprocess",
                "protocol_write_policy": "disabled" if self.blocks_protocol_writes else "legacy_interpreter",
                "local_semantic_write_policy": (
                    "disabled" if self.blocks_local_semantic_writes else "legacy_semantic_policy"
                ),
                "surface_payload_policy": self.surface_payload_policy,
            },
        }


@dataclass(frozen=True, slots=True)
class TurnPlanArtifactWriteAuthority:
    """Execution-facing permission for local artifact save/publish candidates."""

    action: str | None
    allowed: bool
    denied_reason: str | None
    authority: str
    source_field_paths: tuple[str, ...]
    target_available: bool
    requires_clarification: bool
    no_write_reason: str | None

    @property
    def blocks_candidate_write(self) -> bool:
        return self.action in {"artifact_save", "artifact_publish"} and not self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "denied_reason": self.denied_reason,
            "authority": self.authority,
            "source_field_paths": list(self.source_field_paths),
            "target_available": self.target_available,
            "requires_clarification": self.requires_clarification,
            "no_write_reason": self.no_write_reason,
        }


@dataclass(frozen=True, slots=True)
class TurnPlanMemoryWriteAuthority:
    """Execution-facing permission for memory write candidates."""

    action: str | None
    allowed: bool
    denied_reason: str | None
    authority: str
    source_field_paths: tuple[str, ...]
    content_available: bool
    no_write_reason: str | None

    @property
    def blocks_candidate_write(self) -> bool:
        return self.action == "memory_write" and not self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "denied_reason": self.denied_reason,
            "authority": self.authority,
            "source_field_paths": list(self.source_field_paths),
            "content_available": self.content_available,
            "no_write_reason": self.no_write_reason,
        }


@dataclass(frozen=True, slots=True)
class TurnPlanConceptWriteAuthority:
    """Execution-facing permission for concept write candidates."""

    action: str | None
    allowed: bool
    denied_reason: str | None
    authority: str
    source_field_paths: tuple[str, ...]
    content_available: bool
    target_available: bool
    candidate_action: str | None
    no_write_reason: str | None

    @property
    def blocks_candidate_write(self) -> bool:
        return self.action == "concept_write" and not self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "denied_reason": self.denied_reason,
            "authority": self.authority,
            "source_field_paths": list(self.source_field_paths),
            "content_available": self.content_available,
            "target_available": self.target_available,
            "candidate_action": self.candidate_action,
            "no_write_reason": self.no_write_reason,
        }


@dataclass(frozen=True, slots=True)
class TurnPlanProtocolWriteAuthority:
    """Execution-facing permission for protocol upsert/update candidates."""

    action: str | None
    allowed: bool
    denied_reason: str | None
    authority: str
    source_field_paths: tuple[str, ...]
    content_available: bool
    target_available: bool
    candidate_action: str | None
    no_write_reason: str | None

    @property
    def blocks_candidate_write(self) -> bool:
        return self.action == "protocol_write" and not self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "denied_reason": self.denied_reason,
            "authority": self.authority,
            "source_field_paths": list(self.source_field_paths),
            "content_available": self.content_available,
            "target_available": self.target_available,
            "candidate_action": self.candidate_action,
            "no_write_reason": self.no_write_reason,
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
class WriteLedgerEntry:
    category: str
    field_paths: tuple[str, ...]
    status: str | None
    target_kind: str | None
    target_id: str | None
    operation: str | None
    requires_confirmation: bool | None
    committed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "field_paths": list(self.field_paths),
            "status": self.status,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "operation": self.operation,
            "requires_confirmation": self.requires_confirmation,
            "committed": self.committed,
        }


@dataclass(frozen=True, slots=True)
class WriteLedgerPlan:
    categories: tuple[str, ...]
    entries: tuple[WriteLedgerEntry, ...]
    has_write_side_effects: bool
    actual_write_effect_count: int
    committed_write_count: int
    proposed_write_count: int
    no_write_reason: str | None
    effect_field_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "categories": list(self.categories),
            "has_write_side_effects": self.has_write_side_effects,
            "actual_write_effect_count": self.actual_write_effect_count,
            "committed_write_count": self.committed_write_count,
            "proposed_write_count": self.proposed_write_count,
            "no_write_reason": self.no_write_reason,
            "effect_field_paths": list(self.effect_field_paths),
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class WriteProjectionPlan:
    intended_write_kind: str | None
    intended_write_kinds: tuple[str, ...]
    authority: str
    sources: tuple[dict[str, Any], ...]
    structured_source_count: int
    actual_write_categories: tuple[str, ...]
    actual_write_effect_count: int
    effect_agreement: str
    compatibility_projection: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intended_write_kind": self.intended_write_kind,
            "intended_write_kinds": list(self.intended_write_kinds),
            "authority": self.authority,
            "sources": [dict(source) for source in self.sources],
            "structured_source_count": self.structured_source_count,
            "actual_write_categories": list(self.actual_write_categories),
            "actual_write_effect_count": self.actual_write_effect_count,
            "effect_agreement": self.effect_agreement,
            "compatibility_projection": dict(self.compatibility_projection),
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
    local_semantic_write_policy: str
    trace_final_response: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "chat_whiteboard_mode": self.chat_whiteboard_mode,
            "suppress_auto_graph_writes": self.suppress_auto_graph_writes,
            "surface_payload_policy": self.surface_payload_policy,
            "artifact_action_policy": self.artifact_action_policy,
            "local_semantic_write_policy": self.local_semantic_write_policy,
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
class TurnPlanValidation:
    warnings: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        warnings = [dict(warning) for warning in self.warnings]
        return {
            "status": "ok" if not warnings else "warning",
            "warning_count": len(warnings),
            "warnings": warnings,
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
    write_ledger: WriteLedgerPlan
    write_projection: WriteProjectionPlan
    artifact_write_authority: TurnPlanArtifactWriteAuthority
    memory_write_authority: TurnPlanMemoryWriteAuthority
    concept_write_authority: TurnPlanConceptWriteAuthority
    protocol_write_authority: TurnPlanProtocolWriteAuthority
    protocols: ProtocolPlan
    semantic: SemanticPlan
    execution: ExecutionPlan
    compatibility: CompatibilityPlan
    validation: TurnPlanValidation

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
            "write_ledger": self.write_ledger.to_dict(),
            "write_projection": self.write_projection.to_dict(),
            "artifact_write_authority": self.artifact_write_authority.to_dict(),
            "memory_write_authority": self.memory_write_authority.to_dict(),
            "concept_write_authority": self.concept_write_authority.to_dict(),
            "protocol_write_authority": self.protocol_write_authority.to_dict(),
            "protocols": self.protocols.to_dict(),
            "semantic": self.semantic.to_dict(),
            "execution": self.execution.to_dict(),
            "compatibility": self.compatibility.to_dict(),
            "validation": self.validation.to_dict(),
            "authority": {
                "retrieval": self.retrieval.authority,
                "ui_surface_action": self.ui_surface_action.authority,
                "write_intent": self.write_intent.authority,
            },
        }


class TurnPlanBuilder:
    """Build an internal TurnPlan from finalized turn fields."""

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
        side_effect_policy = self._side_effect_policy(request_payload, response_payload, write_intent)
        write_ledger = self._write_ledger_plan(response_payload, write_intent, ui_surface_action)
        route = self._route_plan(response_payload)
        protocols = self._protocol_plan(response_payload)
        semantic = self._semantic_plan(response_payload)
        write_projection = self._write_projection_plan(
            request_payload=request_payload,
            response_payload=response_payload,
            route=route,
            write_intent=write_intent,
            write_ledger=write_ledger,
            semantic=semantic,
        )
        artifact_write_authority = self._artifact_write_authority_plan(
            request_payload=request_payload,
            write_projection=write_projection,
            semantic=semantic,
            side_effect_policy=side_effect_policy,
        )
        memory_write_authority = self._memory_write_authority_plan(
            request_payload=request_payload,
            response_payload=response_payload,
            write_projection=write_projection,
            side_effect_policy=side_effect_policy,
        )
        concept_write_authority = self._concept_write_authority_plan(
            request_payload=request_payload,
            response_payload=response_payload,
            write_projection=write_projection,
            side_effect_policy=side_effect_policy,
        )
        protocol_write_authority = self._protocol_write_authority_plan(
            request_payload=request_payload,
            response_payload=response_payload,
            write_projection=write_projection,
            side_effect_policy=side_effect_policy,
        )
        execution = self._execution_plan(response_payload, write_intent, side_effect_policy, ui_surface_action)
        compatibility = self._compatibility_plan(response_payload, write_intent)
        validation = self._validation_plan(
            request_payload=request_payload,
            response_payload=response_payload,
            route=route,
            retrieval=retrieval,
            visible_context=visible_context,
            ui_surface_action=ui_surface_action,
            write_intent=write_intent,
            side_effect_policy=side_effect_policy,
            write_ledger=write_ledger,
            write_projection=write_projection,
            artifact_write_authority=artifact_write_authority,
            memory_write_authority=memory_write_authority,
            concept_write_authority=concept_write_authority,
            protocol_write_authority=protocol_write_authority,
            semantic=semantic,
            execution=execution,
        )
        return TurnPlan(
            version=TURN_PLAN_VERSION,
            request=request,
            route=route,
            retrieval=retrieval,
            visible_context=visible_context,
            ui_surface_action=ui_surface_action,
            write_intent=write_intent,
            side_effect_policy=side_effect_policy,
            write_ledger=write_ledger,
            write_projection=write_projection,
            artifact_write_authority=artifact_write_authority,
            memory_write_authority=memory_write_authority,
            concept_write_authority=concept_write_authority,
            protocol_write_authority=protocol_write_authority,
            protocols=protocols,
            semantic=semantic,
            execution=execution,
            compatibility=compatibility,
            validation=validation,
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
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        surface_action = _optional_dict(response_payload.get("surface_action")) or _optional_dict(
            invocation.get("surface_action")
        )
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
        if _optional_str(invocation.get("intent")) == "preserve_visible_surface":
            return UiSurfaceActionPlan(
                surface="none",
                mode="preserve",
                target_resource_id=None,
                target_resource_kind=_preserve_surface_target_kind(response_payload),
                active_surface_id=_optional_str(response_payload.get("active_surface_id")),
                authority=_surface_authority(invocation, {}, "none"),
                requires_explicit_signal=True,
                reason=_optional_str(invocation.get("reason")),
            )
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
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        write_intent: WriteIntentPlan,
    ) -> SideEffectPolicy:
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        surface_action = _optional_dict(response_payload.get("surface_action"))
        intent = _optional_str(invocation.get("intent"))
        artifact_qna = intent in {"current_artifact_followup", "selected_material_question"}
        artifact_context = _payload_has_openable_artifact_context(response_payload)
        preserve_surface = intent == "preserve_visible_surface"
        open_only = write_intent.write_behavior == "open_only"
        explicit_write_authority = _payload_has_explicit_write_authority(
            request_payload,
            response_payload,
            write_intent,
        )
        suppress_reason = None
        if surface_action is not None:
            suppress_reason = "close_visible_surface"
        elif preserve_surface:
            suppress_reason = "preserve_visible_surface"
        elif open_only:
            suppress_reason = "open_only_ui_handoff"
        elif artifact_qna and artifact_context and not explicit_write_authority:
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

    def _write_ledger_plan(
        self,
        response_payload: dict[str, Any],
        write_intent: WriteIntentPlan,
        ui_surface_action: UiSurfaceActionPlan,
    ) -> WriteLedgerPlan:
        entries: list[WriteLedgerEntry] = []
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        write_behavior = _normalized_write_behavior(invocation)
        surface_action = _optional_dict(response_payload.get("surface_action"))

        if write_behavior == "open_only":
            entries.append(
                WriteLedgerEntry(
                    category="open_only_no_write",
                    field_paths=("surface_invocation.write_behavior",),
                    status="no_write",
                    target_kind=ui_surface_action.target_resource_kind or ui_surface_action.surface,
                    target_id=ui_surface_action.target_resource_id,
                    operation="ui_open",
                    requires_confirmation=None,
                    committed=False,
                )
            )

        workspace_update = _optional_dict(response_payload.get("workspace_update"))
        if workspace_update is not None:
            entries.append(_workspace_update_ledger_entry(workspace_update))

        graph_action = _optional_dict(response_payload.get("graph_action"))
        created_record = _optional_dict(response_payload.get("created_record"))
        if graph_action is not None or created_record is not None:
            entries.append(_record_write_ledger_entry(graph_action=graph_action, created_record=created_record))

        for index, action in enumerate(_list_of_dicts(response_payload.get("artifact_actions"))):
            entries.append(_artifact_action_ledger_entry(action, index=index))

        if not entries:
            entries.append(
                WriteLedgerEntry(
                    category="none",
                    field_paths=(),
                    status="no_write",
                    target_kind=None,
                    target_id=None,
                    operation=None,
                    requires_confirmation=None,
                    committed=False,
                )
            )

        categories = _dedupe(entry.category for entry in entries)
        effect_entries = tuple(entry for entry in entries if entry.category not in NO_WRITE_LEDGER_CATEGORIES)
        effect_field_paths = _dedupe(path for entry in effect_entries for path in entry.field_paths)
        return WriteLedgerPlan(
            categories=categories,
            entries=tuple(entries),
            has_write_side_effects=bool(effect_entries),
            actual_write_effect_count=len(effect_entries),
            committed_write_count=sum(1 for entry in effect_entries if entry.committed),
            proposed_write_count=sum(1 for entry in effect_entries if not entry.committed),
            no_write_reason=_write_ledger_no_write_reason(
                entries=entries,
                write_intent=write_intent,
                surface_action=surface_action,
                invocation=invocation,
            ),
            effect_field_paths=effect_field_paths,
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

    def _write_projection_plan(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        route: RoutePlan,
        write_intent: WriteIntentPlan,
        write_ledger: WriteLedgerPlan,
        semantic: SemanticPlan,
    ) -> WriteProjectionPlan:
        sources = _structured_write_intent_sources(
            request_payload=request_payload,
            response_payload=response_payload,
            route=route,
            write_intent=write_intent,
            semantic=semantic,
        )
        structured_source_count = len(sources)
        effect_sources = _effect_write_sources(write_ledger)
        all_sources = tuple([*sources, *effect_sources])
        intended_kinds = _dedupe(source.get("kind") for source in all_sources)
        actual_categories = tuple(category for category in write_ledger.categories if category not in NO_WRITE_LEDGER_CATEGORIES)
        authority = "none"
        if sources:
            authority = str(sources[0].get("source") or "structured_intent")
        elif effect_sources:
            authority = "existing_write_effect"
        return WriteProjectionPlan(
            intended_write_kind=intended_kinds[0] if intended_kinds else None,
            intended_write_kinds=intended_kinds,
            authority=authority,
            sources=all_sources,
            structured_source_count=structured_source_count,
            actual_write_categories=actual_categories,
            actual_write_effect_count=write_ledger.actual_write_effect_count,
            effect_agreement=_write_projection_agreement(
                intended_kinds=intended_kinds,
                actual_categories=actual_categories,
                has_structured_sources=bool(sources),
                has_effect_sources=bool(effect_sources),
            ),
            compatibility_projection=_write_projection_compatibility(response_payload),
        )

    def _artifact_write_authority_plan(
        self,
        *,
        request_payload: dict[str, Any],
        write_projection: WriteProjectionPlan,
        semantic: SemanticPlan,
        side_effect_policy: SideEffectPolicy,
    ) -> TurnPlanArtifactWriteAuthority:
        sources = tuple(
            source
            for source in write_projection.sources
            if source.get("kind") in {"artifact_save", "artifact_publish"}
            and source.get("source") != "existing_write_effect"
        )
        action = _artifact_write_action_from_semantic(semantic)
        if action is None and sources:
            action = str(sources[0].get("kind") or "").strip() or None
        source_field_paths = tuple(
            path
            for path in (_optional_str(source.get("field_path")) for source in sources)
            if path
        )
        requires_clarification = bool(semantic.should_clarify and action in {"artifact_save", "artifact_publish"})
        target_available = _artifact_write_target_available(
            request_payload=request_payload,
            requires_clarification=requires_clarification,
        )
        no_write_reason = side_effect_policy.suppress_auto_graph_writes_reason
        denied_reason = None
        allowed = False
        if action is None:
            denied_reason = None
        elif no_write_reason is not None:
            denied_reason = no_write_reason
        elif not sources:
            denied_reason = "missing_structured_artifact_write_intent"
        elif requires_clarification or not target_available:
            denied_reason = "artifact_write_target_unavailable_or_ambiguous"
        else:
            allowed = True
        return TurnPlanArtifactWriteAuthority(
            action=action,
            allowed=allowed,
            denied_reason=denied_reason,
            authority=str(sources[0].get("source") or "structured_intent") if sources else "none",
            source_field_paths=source_field_paths,
            target_available=target_available,
            requires_clarification=requires_clarification,
            no_write_reason=no_write_reason,
        )

    def _memory_write_authority_plan(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        write_projection: WriteProjectionPlan,
        side_effect_policy: SideEffectPolicy,
    ) -> TurnPlanMemoryWriteAuthority:
        sources = tuple(
            source
            for source in write_projection.sources
            if source.get("kind") == "memory_write"
            and source.get("source") != "existing_write_effect"
        )
        has_memory_effect = any(
            source.get("kind") == "memory_write" and source.get("source") == "existing_write_effect"
            for source in write_projection.sources
        )
        action = (
            "memory_write"
            if sources or has_memory_effect or _has_memory_write_candidate(response_payload)
            else None
        )
        source_field_paths = tuple(
            path
            for path in (_optional_str(source.get("field_path")) for source in sources)
            if path
        )
        content_available = _memory_write_content_available(
            request_payload=request_payload,
            response_payload=response_payload,
        )
        no_write_reason = side_effect_policy.suppress_auto_graph_writes_reason
        denied_reason = None
        allowed = False
        if action is None:
            denied_reason = None
        elif no_write_reason is not None:
            denied_reason = no_write_reason
        elif not sources:
            denied_reason = "missing_structured_memory_write_intent"
        elif not content_available:
            denied_reason = "memory_write_content_unavailable_or_unsafe"
        else:
            allowed = True
        return TurnPlanMemoryWriteAuthority(
            action=action,
            allowed=allowed,
            denied_reason=denied_reason,
            authority=str(sources[0].get("source") or "structured_intent") if sources else "none",
            source_field_paths=source_field_paths,
            content_available=content_available,
            no_write_reason=no_write_reason,
        )

    def _concept_write_authority_plan(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        write_projection: WriteProjectionPlan,
        side_effect_policy: SideEffectPolicy,
    ) -> TurnPlanConceptWriteAuthority:
        sources = tuple(
            source
            for source in write_projection.sources
            if source.get("kind") == "concept_write"
            and source.get("source") != "existing_write_effect"
        )
        has_concept_effect = any(
            source.get("kind") == "concept_write" and source.get("source") == "existing_write_effect"
            for source in write_projection.sources
        )
        candidate_action = _concept_write_candidate_action(response_payload)
        action = "concept_write" if sources or has_concept_effect or candidate_action is not None else None
        source_field_paths = tuple(
            path
            for path in (_optional_str(source.get("field_path")) for source in sources)
            if path
        )
        content_available = _concept_write_content_available(
            request_payload=request_payload,
            response_payload=response_payload,
        )
        target_available = _concept_write_target_available(
            response_payload=response_payload,
            candidate_action=candidate_action,
        )
        no_write_reason = side_effect_policy.suppress_auto_graph_writes_reason
        denied_reason = None
        allowed = False
        if action is None:
            denied_reason = None
        elif no_write_reason is not None:
            denied_reason = no_write_reason
        elif not sources:
            denied_reason = "missing_structured_concept_write_intent"
        elif not content_available:
            denied_reason = "concept_write_content_unavailable_or_unsafe"
        elif not target_available:
            denied_reason = "concept_write_target_unavailable_or_ambiguous"
        else:
            allowed = True
        return TurnPlanConceptWriteAuthority(
            action=action,
            allowed=allowed,
            denied_reason=denied_reason,
            authority=str(sources[0].get("source") or "structured_intent") if sources else "none",
            source_field_paths=source_field_paths,
            content_available=content_available,
            target_available=target_available,
            candidate_action=candidate_action,
            no_write_reason=no_write_reason,
        )

    def _protocol_write_authority_plan(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        write_projection: WriteProjectionPlan,
        side_effect_policy: SideEffectPolicy,
    ) -> TurnPlanProtocolWriteAuthority:
        sources = tuple(
            source
            for source in write_projection.sources
            if source.get("kind") == "protocol_write"
            and source.get("source") != "existing_write_effect"
        )
        has_protocol_effect = any(
            source.get("kind") == "protocol_write" and source.get("source") == "existing_write_effect"
            for source in write_projection.sources
        )
        candidate_action = _protocol_write_candidate_action(response_payload)
        action = "protocol_write" if sources or has_protocol_effect or candidate_action is not None else None
        existing_authority = _dict_or_empty(response_payload.get("protocol_write_authority"))
        source_field_paths = tuple(
            path
            for path in (_optional_str(source.get("field_path")) for source in sources)
            if path
        )
        if not source_field_paths and isinstance(existing_authority.get("source_field_paths"), list):
            source_field_paths = tuple(
                path
                for path in (_optional_str(item) for item in existing_authority["source_field_paths"])
                if path
            )
        content_available = _protocol_write_content_available(
            request_payload=request_payload,
            response_payload=response_payload,
            has_protocol_effect=has_protocol_effect,
        )
        target_available = _protocol_write_target_available(
            request_payload=request_payload,
            response_payload=response_payload,
            has_protocol_effect=has_protocol_effect,
        )
        existing_policy_allowed = request_payload.get("protocol_write_allowed_by_existing_policy")
        prior_denied_reason = _optional_str(existing_authority.get("denied_reason"))
        prior_allowed = existing_authority.get("allowed")
        no_write_reason = side_effect_policy.suppress_auto_graph_writes_reason
        denied_reason = None
        allowed = False
        if action is None:
            denied_reason = None
        elif no_write_reason is not None:
            denied_reason = no_write_reason
        elif existing_policy_allowed is False:
            denied_reason = "protocol_write_blocked_by_existing_policy"
        elif prior_allowed is False and prior_denied_reason:
            denied_reason = prior_denied_reason
        elif not sources:
            denied_reason = "missing_structured_protocol_write_intent"
        elif not content_available:
            denied_reason = "protocol_write_content_unavailable_or_unsafe"
        elif not target_available:
            denied_reason = "protocol_write_target_unavailable_or_ambiguous"
        else:
            allowed = True
        return TurnPlanProtocolWriteAuthority(
            action=action,
            allowed=allowed,
            denied_reason=denied_reason,
            authority=(
                str(sources[0].get("source") or "structured_intent")
                if sources
                else (_optional_str(existing_authority.get("authority")) or "none")
            ),
            source_field_paths=source_field_paths,
            content_available=content_available,
            target_available=target_available,
            candidate_action=candidate_action,
            no_write_reason=no_write_reason,
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
            local_semantic_write_policy=(
                "disabled"
                if side_effect_policy.suppress_auto_graph_writes_reason
                in {"open_only_ui_handoff", "close_visible_surface", "preserve_visible_surface"}
                else "legacy_semantic_policy"
            ),
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

    def _validation_plan(
        self,
        *,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        route: RoutePlan,
        retrieval: RetrievalPlan,
        visible_context: VisibleContextPlan,
        ui_surface_action: UiSurfaceActionPlan,
        write_intent: WriteIntentPlan,
        side_effect_policy: SideEffectPolicy,
        write_ledger: WriteLedgerPlan,
        write_projection: WriteProjectionPlan,
        artifact_write_authority: TurnPlanArtifactWriteAuthority,
        memory_write_authority: TurnPlanMemoryWriteAuthority,
        concept_write_authority: TurnPlanConceptWriteAuthority,
        protocol_write_authority: TurnPlanProtocolWriteAuthority,
        semantic: SemanticPlan,
        execution: ExecutionPlan,
    ) -> TurnPlanValidation:
        warnings: list[dict[str, Any]] = []
        invocation = _dict_or_empty(response_payload.get("surface_invocation"))
        intent = _optional_str(invocation.get("intent"))
        primary_surface = _optional_str(invocation.get("primary_surface")) or "chat"
        write_behavior = write_intent.write_behavior
        surface_action = _optional_dict(response_payload.get("surface_action"))
        action_type = _optional_str(surface_action.get("type")) if surface_action else None
        control_actions = _control_panel_action_types(route.control_panel)
        active_surface_id = _optional_str(response_payload.get("active_surface_id"))
        surface_payloads = _list_of_dicts(response_payload.get("surface_payloads"))
        write_side_effects = list(write_ledger.effect_field_paths)
        explicit_open_authority = bool(
            (retrieval.navigator_selection or {}).get("surface_to_open")
            or "open_whiteboard" in control_actions
            or "open_calendar" in control_actions
            or "open_surface" in control_actions
        )
        invocation_target_resource_id = _surface_target_resource_id(invocation)

        if (
            retrieval.selected_resource_ids
            and ui_surface_action.surface not in {"none", "chat"}
            and ui_surface_action.mode in {"open_only", "foreground_existing"}
            and not explicit_open_authority
            and (intent == "attention_selected_context" or ui_surface_action.surface == "whiteboard")
        ):
            warnings.append(
                _validation_warning(
                    "selected_context_open_without_authority",
                    "Selected context is foregrounding a UI surface without an explicit Navigator/control-plane open signal.",
                    [
                        "retrieval.selected_resource_ids",
                        "navigator_selection.surface_to_open",
                        "surface_invocation.primary_surface",
                        "surface_invocation.write_behavior",
                    ],
                )
            )

        if write_behavior == "open_only" and write_side_effects:
            warnings.append(
                _validation_warning(
                    "open_only_with_write_side_effect",
                    "A UI-only open handoff carried write side effects.",
                    ["surface_invocation.write_behavior", *write_side_effects],
                )
            )

        material_open = (
            ui_surface_action.surface == "whiteboard"
            and ui_surface_action.mode in {"open_only", "foreground_existing"}
            and (explicit_open_authority or write_behavior == "open_only")
        )
        if material_open:
            selected_targets = set(retrieval.selected_resource_ids)
            selected_targets.update(_navigator_selected_ids(retrieval.navigator_selection))
            target = ui_surface_action.target_resource_id
            if (
                target is None
                or not _is_openable_resource_id(target)
                or (selected_targets and target not in selected_targets)
            ):
                warnings.append(
                    _validation_warning(
                        "saved_artifact_open_target_not_selected",
                        "A Whiteboard open handoff did not target a selected openable artifact/workspace resource.",
                        [
                            "navigator_selection.primary_resource_id",
                            "navigator_selection.selected_ids",
                            "selected_attention_resources",
                            "surface_invocation.primary_surface",
                            "surface_invocation.write_behavior",
                        ],
                    )
                )
        if (
            invocation_target_resource_id
            and retrieval.primary_resource_id
            and invocation_target_resource_id != retrieval.primary_resource_id
            and ui_surface_action.surface == "whiteboard"
        ):
            warnings.append(
                _validation_warning(
                    "ui_open_target_conflicts_with_selected_primary",
                    "The UI open target conflicts with the selected primary resource.",
                    [
                        "navigator_selection.primary_resource_id",
                        "surface_invocation.target_resource_id",
                    ],
                )
            )

        preserve_surface = intent == "preserve_visible_surface" or "preserve_surface" in control_actions
        if preserve_surface:
            if (
                primary_surface != "chat"
                or ui_surface_action.surface != "none"
                or write_behavior != "none"
                or active_surface_id is not None
                or surface_payloads
            ):
                warnings.append(
                    _validation_warning(
                        "preserve_surface_reclassified",
                        "A preserve/no-op surface intent was reclassified into a foreground/open surface result.",
                        [
                            "turn_interpretation.control_panel.actions",
                            "surface_invocation.primary_surface",
                            "surface_invocation.write_behavior",
                            "active_surface_id",
                            "surface_payloads",
                        ],
                    )
                )
            if surface_action is not None:
                warnings.append(
                    _validation_warning(
                        "preserve_surface_has_surface_action",
                        "A preserve/no-op surface intent also emitted a surface action.",
                        ["turn_interpretation.control_panel.actions", "surface_action"],
                    )
                )
            if write_side_effects:
                warnings.append(
                    _validation_warning(
                        "preserve_surface_has_write_side_effects",
                        "A preserve/no-op surface intent carried write side effects.",
                        ["turn_interpretation.control_panel.actions", *write_side_effects],
                    )
                )

        close_surface = action_type == "close_visible_surface" or intent == "close_visible_surface"
        if close_surface:
            if (
                primary_surface != "chat"
                or ui_surface_action.mode in {
                    "open_only",
                    "read_only",
                    "draft",
                    "proposal_only",
                    "artifact_branching",
                    "foreground_existing",
                }
                or active_surface_id is not None
                or surface_payloads
            ):
                warnings.append(
                    _validation_warning(
                        "close_surface_reclassified",
                        "A close-visible-surface intent was reclassified into an open/foreground surface result.",
                        [
                            "surface_action",
                            "surface_invocation.primary_surface",
                            "surface_invocation.write_behavior",
                            "active_surface_id",
                            "surface_payloads",
                        ],
                    )
                )
            if write_side_effects:
                warnings.append(
                    _validation_warning(
                        "close_surface_with_write_side_effect",
                        "A close-visible-surface intent carried write side effects.",
                        ["surface_action", *write_side_effects],
                    )
                )
            if _has_deletion_semantics(response_payload):
                warnings.append(
                    _validation_warning(
                        "close_surface_has_deletion_semantics",
                        "A close-visible-surface intent included deletion-like artifact action semantics.",
                        ["surface_action", "artifact_actions"],
                    )
                )

        artifact_qna = intent in {"current_artifact_followup", "selected_material_question"}
        artifact_context_chat = artifact_qna or (
            route.mode == "chat"
            and primary_surface == "chat"
            and write_behavior == "none"
            and (
                bool(visible_context.incoming_visible_artifact_ids)
                or bool(visible_context.response_visible_artifact_ids)
                or any(_is_openable_resource_id(resource_id) for resource_id in retrieval.selected_resource_ids)
            )
        )
        if (
            artifact_context_chat
            and write_side_effects
            and not _has_explicit_write_authority(route, write_intent, semantic, request_payload, response_payload)
        ):
            warnings.append(
                _validation_warning(
                    "visible_artifact_qna_with_durable_write",
                    "A chat-first visible/selected artifact Q&A turn carried durable write side effects without explicit write authority.",
                    ["surface_invocation.intent", *write_side_effects],
                )
            )

        if (
            side_effect_policy.actual_workspace_update
            and write_intent.kind not in {"whiteboard_draft", "whiteboard_offer", "scenario_branching"}
            and not write_intent.explicit_user_intent
        ):
            warnings.append(
                _validation_warning(
                    "workspace_update_without_write_intent",
                    "A workspace update appeared without a draft/offer/write intent.",
                    ["workspace_update", "write_intent.kind", "write_intent.explicit_user_intent"],
                )
            )

        if (
            (write_behavior == "draft_only" or write_intent.whiteboard_mode == "draft")
            and (ui_surface_action.surface != "whiteboard" or write_intent.kind != "whiteboard_draft")
        ):
            warnings.append(
                _validation_warning(
                    "draft_intent_surface_mismatch",
                    "A draft/write intent did not align with a Whiteboard draft plan.",
                    ["surface_invocation", "ui_surface_action", "write_intent"],
                )
            )

        operational_surface = ui_surface_action.surface in {"calendar_day", "calendar_week", "today_briefing", "task_focus"}
        if operational_surface:
            surface_payload_ids = {
                item_id for item_id in (_item_id(payload) for payload in surface_payloads) if item_id
            }
            if active_surface_id and surface_payloads and active_surface_id not in surface_payload_ids:
                warnings.append(
                    _validation_warning(
                        "surface_payload_mismatch",
                        "The active operational surface id does not match returned surface payloads.",
                        ["active_surface_id", "surface_payloads"],
                    )
                )
            if active_surface_id and not surface_payloads:
                warnings.append(
                    _validation_warning(
                        "surface_payload_mismatch",
                        "An operational active surface id was returned without a matching surface payload.",
                        ["active_surface_id", "surface_payloads"],
                    )
                )
            if surface_payloads and not active_surface_id:
                warnings.append(
                    _validation_warning(
                        "surface_payload_mismatch",
                        "Operational surface payloads were returned without an active surface id.",
                        ["active_surface_id", "surface_payloads"],
                    )
                )

        for field in _calendar_task_mutation_fields(response_payload):
            warnings.append(
                _validation_warning(
                    "mutation_without_confirmation",
                    "A calendar/task mutation was not represented as a proposal-only action requiring confirmation.",
                    [field, "surface_invocation.write_behavior"],
                )
            )

        if write_ledger.has_write_side_effects and not write_projection.sources:
            warnings.append(
                _validation_warning(
                    "write_effect_without_projected_intent",
                    "Finalized write effects exist, but TurnPlan did not project any write intent source.",
                    [*write_side_effects, "turn_plan.write_projection.sources"],
                )
            )

        if (
            write_ledger.has_write_side_effects
            and write_projection.structured_source_count == 0
            and write_projection.compatibility_projection.get("surface_invocation_write_behavior") == "none"
            and not write_projection.compatibility_projection.get("surface_invocation_has_write_intent")
        ):
            warnings.append(
                _validation_warning(
                    "compatibility_no_write_with_write_effect",
                    "Compatibility surface fields claimed no write while finalized write effects were present.",
                    [*write_side_effects, "surface_invocation.write_behavior", "surface_invocation.write_intent"],
                )
            )

        if (
            "artifact_save_or_promotion" in write_ledger.categories
            and not artifact_write_authority.allowed
            and artifact_write_authority.action in {"artifact_save", "artifact_publish"}
        ):
            warnings.append(
                _validation_warning(
                    "artifact_write_effect_without_authority",
                    "An artifact save/publish effect appeared after TurnPlan denied artifact write authority.",
                    [
                        "turn_plan.artifact_write_authority",
                        *write_side_effects,
                    ],
                )
            )

        if (
            "memory_write" in write_ledger.categories
            and not memory_write_authority.allowed
            and memory_write_authority.action == "memory_write"
        ):
            warnings.append(
                _validation_warning(
                    "memory_write_effect_without_authority",
                    "A memory write effect appeared after TurnPlan denied memory write authority.",
                    [
                        "turn_plan.memory_write_authority",
                        *write_side_effects,
                    ],
                )
            )

        has_non_protocol_concept_effect = any(
            entry.category == "concept_write"
            and str(entry.target_kind or "").strip().lower() != "protocol"
            and str(entry.operation or "").strip().lower() != "upsert_protocol"
            for entry in write_ledger.entries
        )
        has_protocol_effect = any(
            entry.category == "concept_write"
            and (
                str(entry.target_kind or "").strip().lower() == "protocol"
                or str(entry.operation or "").strip().lower() == "upsert_protocol"
            )
            for entry in write_ledger.entries
        )
        if (
            has_non_protocol_concept_effect
            and not concept_write_authority.allowed
            and concept_write_authority.action == "concept_write"
        ):
            warnings.append(
                _validation_warning(
                    "concept_write_effect_without_authority",
                    "A concept write effect appeared after TurnPlan denied concept write authority.",
                    [
                        "turn_plan.concept_write_authority",
                        *write_side_effects,
                    ],
                )
            )
        if (
            has_protocol_effect
            and not protocol_write_authority.allowed
            and protocol_write_authority.action == "protocol_write"
        ):
            warnings.append(
                _validation_warning(
                    "protocol_write_effect_without_authority",
                    "A protocol write effect appeared after TurnPlan denied protocol write authority.",
                    [
                        "turn_plan.protocol_write_authority",
                        *write_side_effects,
                    ],
                )
            )

        return TurnPlanValidation(warnings=tuple(warnings))


def turn_plan_trace_payload(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    return TurnPlanBuilder().build(
        request_payload=request_payload,
        response_payload=response_payload,
    ).to_dict()


def build_turn_plan_surface_authority(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> TurnPlanSurfaceAuthority:
    """Build the internal TurnPlan surface-action contract from finalized fields.

    This is intentionally narrower than full TurnPlan execution authority: it
    centralizes open/close/preserve surface application while leaving write and
    retrieval behavior on the existing paths for this migration slice.
    """

    payload = _with_nested_surface_action(response_payload)
    builder = TurnPlanBuilder()
    retrieval = builder._retrieval_plan(payload)
    ui_surface_action = builder._ui_surface_action_plan(payload, retrieval)
    write_intent = builder._write_intent_plan(payload, ui_surface_action)
    side_effect_policy = builder._side_effect_policy(request_payload or {}, payload, write_intent)
    surface_invocation = _dict_or_empty(payload.get("surface_invocation"))
    surface_action = _optional_dict(payload.get("surface_action"))
    return TurnPlanSurfaceAuthority(
        ui_surface_action=ui_surface_action,
        write_intent=write_intent,
        side_effect_policy=side_effect_policy,
        surface_invocation=surface_invocation,
        surface_action=surface_action,
    )


def build_turn_plan_artifact_write_authority(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> TurnPlanArtifactWriteAuthority:
    """Build the TurnPlan permission gate for artifact save/publish candidates."""

    payload = _with_nested_surface_action(response_payload)
    builder = TurnPlanBuilder()
    retrieval = builder._retrieval_plan(payload)
    ui_surface_action = builder._ui_surface_action_plan(payload, retrieval)
    write_intent = builder._write_intent_plan(payload, ui_surface_action)
    side_effect_policy = builder._side_effect_policy(request_payload or {}, payload, write_intent)
    write_ledger = builder._write_ledger_plan(payload, write_intent, ui_surface_action)
    route = builder._route_plan(payload)
    semantic = builder._semantic_plan(payload)
    write_projection = builder._write_projection_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        route=route,
        write_intent=write_intent,
        write_ledger=write_ledger,
        semantic=semantic,
    )
    return builder._artifact_write_authority_plan(
        request_payload=request_payload or {},
        write_projection=write_projection,
        semantic=semantic,
        side_effect_policy=side_effect_policy,
    )


def build_turn_plan_memory_write_authority(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> TurnPlanMemoryWriteAuthority:
    """Build the TurnPlan permission gate for memory write candidates."""

    payload = _with_nested_surface_action(response_payload)
    builder = TurnPlanBuilder()
    retrieval = builder._retrieval_plan(payload)
    ui_surface_action = builder._ui_surface_action_plan(payload, retrieval)
    write_intent = builder._write_intent_plan(payload, ui_surface_action)
    side_effect_policy = builder._side_effect_policy(request_payload or {}, payload, write_intent)
    write_ledger = builder._write_ledger_plan(payload, write_intent, ui_surface_action)
    route = builder._route_plan(payload)
    semantic = builder._semantic_plan(payload)
    write_projection = builder._write_projection_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        route=route,
        write_intent=write_intent,
        write_ledger=write_ledger,
        semantic=semantic,
    )
    return builder._memory_write_authority_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        write_projection=write_projection,
        side_effect_policy=side_effect_policy,
    )


def build_turn_plan_concept_write_authority(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> TurnPlanConceptWriteAuthority:
    """Build the TurnPlan permission gate for concept write candidates."""

    payload = _with_nested_surface_action(response_payload)
    builder = TurnPlanBuilder()
    retrieval = builder._retrieval_plan(payload)
    ui_surface_action = builder._ui_surface_action_plan(payload, retrieval)
    write_intent = builder._write_intent_plan(payload, ui_surface_action)
    side_effect_policy = builder._side_effect_policy(request_payload or {}, payload, write_intent)
    write_ledger = builder._write_ledger_plan(payload, write_intent, ui_surface_action)
    route = builder._route_plan(payload)
    semantic = builder._semantic_plan(payload)
    write_projection = builder._write_projection_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        route=route,
        write_intent=write_intent,
        write_ledger=write_ledger,
        semantic=semantic,
    )
    return builder._concept_write_authority_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        write_projection=write_projection,
        side_effect_policy=side_effect_policy,
    )


def build_turn_plan_protocol_write_authority(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> TurnPlanProtocolWriteAuthority:
    """Build the TurnPlan permission gate for protocol upsert/update candidates."""

    payload = _with_nested_surface_action(response_payload)
    builder = TurnPlanBuilder()
    retrieval = builder._retrieval_plan(payload)
    ui_surface_action = builder._ui_surface_action_plan(payload, retrieval)
    write_intent = builder._write_intent_plan(payload, ui_surface_action)
    side_effect_policy = builder._side_effect_policy(request_payload or {}, payload, write_intent)
    write_ledger = builder._write_ledger_plan(payload, write_intent, ui_surface_action)
    route = builder._route_plan(payload)
    semantic = builder._semantic_plan(payload)
    write_projection = builder._write_projection_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        route=route,
        write_intent=write_intent,
        write_ledger=write_ledger,
        semantic=semantic,
    )
    return builder._protocol_write_authority_plan(
        request_payload=request_payload or {},
        response_payload=payload,
        write_projection=write_projection,
        side_effect_policy=side_effect_policy,
    )


def project_write_intent_compatibility(
    *,
    response_payload: dict[str, Any],
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a response payload with additive write-intent compatibility fields.

    The projection is intentionally post-execution only. It does not create or
    authorize writes; it annotates the finalized payload so legacy
    ``surface_invocation`` fields do not look like pure chat when structured
    write intent or finalized write effects are already present.
    """

    payload = dict(response_payload)
    plan = TurnPlanBuilder().build(
        request_payload=request_payload or {},
        response_payload=payload,
    )
    projection = plan.write_projection
    if projection.intended_write_kind is None and projection.actual_write_effect_count == 0:
        return payload

    invocation = dict(_dict_or_empty(payload.get("surface_invocation")))
    if not invocation:
        invocation = {
            "policy_version": "surface-invocation-v1",
            "intent": "write_effect",
            "primary_surface": "chat",
            "supporting_surfaces": [],
            "surfaces": [],
            "write_behavior": "none",
            "reason": "Projected from finalized write intent/effects.",
            "confidence": None,
            "whiteboard_mode": "chat",
            "trigger": "write_intent_projection",
        }
    legacy_intent = _optional_str(invocation.get("intent"))
    projected_intent = _surface_intent_for_write_projection(projection.intended_write_kind, legacy_intent)
    if projected_intent and projected_intent != legacy_intent:
        invocation["legacy_intent"] = legacy_intent
        invocation["intent"] = projected_intent

    legacy_write_behavior = _normalized_write_behavior(invocation)
    projected_write_behavior = _surface_write_behavior_for_projection(projection, legacy_write_behavior)
    if projected_write_behavior != legacy_write_behavior:
        invocation["legacy_write_behavior"] = legacy_write_behavior
        invocation["write_behavior"] = projected_write_behavior

    invocation["write_intent"] = {
        "kind": projection.intended_write_kind,
        "kinds": list(projection.intended_write_kinds),
        "authority": projection.authority,
        "sources": [dict(source) for source in projection.sources],
        "effect_agreement": projection.effect_agreement,
    }
    effects = [
        entry.to_dict()
        for entry in plan.write_ledger.entries
        if entry.category not in NO_WRITE_LEDGER_CATEGORIES
    ]
    if effects:
        invocation["write_effects"] = effects
    payload["surface_invocation"] = invocation
    return payload


def _with_nested_surface_action(response_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(response_payload)
    if isinstance(payload.get("surface_action"), dict):
        return payload
    invocation = _dict_or_empty(payload.get("surface_invocation"))
    action = _optional_dict(invocation.get("surface_action"))
    if action is not None:
        payload["surface_action"] = action
    return payload


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


def _preserve_surface_target_kind(response_payload: dict[str, Any]) -> str | None:
    interpretation = _dict_or_empty(response_payload.get("turn_interpretation"))
    control_panel = _dict_or_empty(interpretation.get("control_panel"))
    for action in _list_of_dicts(control_panel.get("actions")):
        action_type = str(action.get("type") or action.get("action") or "").strip()
        if action_type != "preserve_surface":
            continue
        return _optional_str(action.get("target") or action.get("surface") or action.get("target_surface"))
    return None


def _control_panel_has_write_action(interpretation: dict[str, Any]) -> bool:
    control_panel = _dict_or_empty(interpretation.get("control_panel"))
    for action in _list_of_dicts(control_panel.get("actions")):
        action_type = str(action.get("type") or action.get("action") or "").strip()
        if action_type in {
            "draft_whiteboard",
            "save_whiteboard",
            "publish_artifact",
            "remember",
            "create_memory",
            "memory_write",
            "save_memory",
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
            "protocol_write",
            "upsert_protocol",
            "update_protocol",
        }:
            return True
    return False


def _control_panel_action_types(control_panel: dict[str, Any]) -> set[str]:
    return {
        action_type
        for action_type in (
            str(action.get("type") or action.get("action") or "").strip()
            for action in _list_of_dicts(control_panel.get("actions"))
        )
        if action_type
    }


def _structured_write_intent_sources(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    route: RoutePlan,
    write_intent: WriteIntentPlan,
    semantic: SemanticPlan,
) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    memory_intent = _optional_str(request_payload.get("memory_intent"))
    if memory_intent == "remember":
        sources.append(
            _write_source(
                source="memory_intent",
                field_path="request.memory_intent",
                kind="memory_write",
                action=memory_intent,
            )
        )

    for index, action in enumerate(_list_of_dicts(route.control_panel.get("actions"))):
        action_type = str(action.get("type") or action.get("action") or "").strip()
        kind = _control_panel_write_kind(action_type)
        if kind is None:
            continue
        sources.append(
            _write_source(
                source="control_panel",
                field_path=f"turn_interpretation.control_panel.actions[{index}].type",
                kind=kind,
                action=action_type,
            )
        )

    meta_action = _dict_or_empty(response_payload.get("meta_action"))
    meta_action_type = _concept_write_candidate_action(response_payload)
    if meta_action_type is not None:
        field_path = "meta_action.candidate_action"
        if str(meta_action.get("action") or "").strip().lower() == meta_action_type:
            field_path = "meta_action.action"
        elif str(meta_action.get("blocked_action") or "").strip().lower() == meta_action_type:
            field_path = "meta_action.blocked_action"
        sources.append(
            _write_source(
                source="meta_decision",
                field_path=field_path,
                kind="concept_write",
                action=meta_action_type,
            )
        )

    semantic_action = str(semantic.semantic_action or "").strip().lower()
    semantic_kind = _semantic_write_kind(semantic_action)
    if semantic_kind is not None:
        sources.append(
            _write_source(
                source="semantic_policy",
                field_path="semantic_policy.semantic_action",
                kind=semantic_kind,
                action=semantic_action,
            )
        )
    policy_action = str(semantic.policy_action_type or "").strip().lower()
    policy_kind = _semantic_write_kind(policy_action)
    if policy_kind is not None and policy_action != semantic_action:
        sources.append(
            _write_source(
                source="semantic_policy",
                field_path="semantic_policy.action_type",
                kind=policy_kind,
                action=policy_action,
            )
        )

    if write_intent.explicit_user_intent:
        write_kind = _write_intent_kind(write_intent.kind)
        if write_kind is not None:
            sources.append(
                _write_source(
                    source="write_intent",
                    field_path="turn_plan.write_intent.kind",
                    kind=write_kind,
                    action=write_intent.kind,
                )
            )

    protocol_candidate = _dict_or_empty(response_payload.get("protocol_write_candidate"))
    protocol_candidate_action = str(protocol_candidate.get("action") or "").strip().lower()
    if protocol_candidate_action in {"upsert_protocol", "protocol_write"}:
        sources.append(
            _write_source(
                source="protocol_interpreter",
                field_path="protocol_write_candidate.action",
                kind="protocol_write",
                action=protocol_candidate_action,
            )
        )
    else:
        protocol_authority = _dict_or_empty(response_payload.get("protocol_write_authority"))
        protocol_authority_action = str(protocol_authority.get("candidate_action") or "").strip().lower()
        if not protocol_authority_action and str(protocol_authority.get("action") or "").strip().lower() == "protocol_write":
            protocol_authority_action = "protocol_write"
        if protocol_authority.get("allowed") is True and protocol_authority_action in {"upsert_protocol", "protocol_write"}:
            sources.append(
                _write_source(
                    source="protocol_interpreter",
                    field_path="protocol_write_authority.action",
                    kind="protocol_write",
                    action=protocol_authority_action,
                )
            )

    graph_action = _dict_or_empty(response_payload.get("graph_action"))
    created_record = _dict_or_empty(response_payload.get("created_record"))
    graph_action_type = str(graph_action.get("type") or graph_action.get("action") or "").strip()
    created_record_type = str(created_record.get("type") or created_record.get("source") or "").strip()
    if graph_action_type == "upsert_protocol" or created_record_type == "protocol":
        sources.append(
            _write_source(
                source="protocol_interpreter",
                field_path="graph_action.type" if graph_action_type == "upsert_protocol" else "created_record.type",
                kind="protocol_write",
                action=graph_action_type or created_record_type,
            )
        )

    return tuple(_dedupe_write_sources(sources))


def _artifact_write_action_from_semantic(semantic: SemanticPlan) -> str | None:
    for value in (semantic.semantic_action, semantic.policy_action_type):
        kind = _semantic_write_kind(str(value or "").strip().lower())
        if kind in {"artifact_save", "artifact_publish"}:
            return kind
    return None


def _artifact_write_target_available(
    *,
    request_payload: dict[str, Any],
    requires_clarification: bool,
) -> bool:
    if requires_clarification:
        return False
    explicit = request_payload.get("artifact_write_target_available")
    if isinstance(explicit, bool):
        return explicit
    workspace_scope = _optional_str(request_payload.get("workspace_scope"))
    if workspace_scope == "excluded":
        return False
    if isinstance(request_payload.get("workspace_has_content"), bool):
        return bool(request_payload.get("workspace_has_content"))
    return True


def _memory_write_content_available(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any] | None = None,
) -> bool:
    explicit = request_payload.get("memory_write_content_available")
    if isinstance(explicit, bool):
        return explicit
    meta_action = _dict_or_empty((response_payload or {}).get("meta_action"))
    for key in ("title", "card", "body"):
        value = meta_action.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _concept_write_content_available(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any] | None = None,
) -> bool:
    explicit = request_payload.get("concept_write_content_available")
    if isinstance(explicit, bool):
        return explicit
    meta_action = _dict_or_empty((response_payload or {}).get("meta_action"))
    for key in ("title", "card", "body"):
        value = meta_action.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _concept_write_target_available(
    *,
    response_payload: dict[str, Any],
    candidate_action: str | None,
) -> bool:
    if candidate_action != "create_revision":
        return True
    meta_action = _dict_or_empty(response_payload.get("meta_action"))
    return bool(str(meta_action.get("target_concept_id") or "").strip())


def _has_memory_write_candidate(response_payload: dict[str, Any]) -> bool:
    meta_action = _dict_or_empty(response_payload.get("meta_action"))
    blocked_action = str(meta_action.get("blocked_action") or "").strip().lower()
    candidate_action = str(meta_action.get("candidate_action") or "").strip().lower()
    return blocked_action in {"create_memory", "memory_write", "save_memory"} or candidate_action in {
        "create_memory",
        "memory_write",
        "save_memory",
    }


def _concept_write_candidate_action(response_payload: dict[str, Any]) -> str | None:
    meta_action = _dict_or_empty(response_payload.get("meta_action"))
    for key in ("candidate_action", "blocked_action", "action", "type"):
        action = str(meta_action.get(key) or "").strip().lower()
        if action in _CONCEPT_WRITE_ACTIONS:
            return action
    return None


def _protocol_write_candidate_action(response_payload: dict[str, Any]) -> str | None:
    candidate = _dict_or_empty(response_payload.get("protocol_write_candidate"))
    action = str(candidate.get("action") or "").strip().lower()
    if action in {"upsert_protocol", "protocol_write"}:
        return action
    authority = _dict_or_empty(response_payload.get("protocol_write_authority"))
    action = str(authority.get("candidate_action") or "").strip().lower()
    if action in {"upsert_protocol", "protocol_write"}:
        return action
    if str(authority.get("action") or "").strip().lower() == "protocol_write":
        return "protocol_write"
    return None


def _protocol_write_content_available(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    has_protocol_effect: bool,
) -> bool:
    explicit = request_payload.get("protocol_write_content_available")
    if isinstance(explicit, bool):
        return explicit
    authority = _dict_or_empty(response_payload.get("protocol_write_authority"))
    if isinstance(authority.get("content_available"), bool):
        return bool(authority.get("content_available"))
    candidate = _dict_or_empty(response_payload.get("protocol_write_candidate"))
    if isinstance(candidate.get("content_available"), bool):
        return bool(candidate.get("content_available"))
    if has_protocol_effect:
        return True
    for key in ("title", "card", "body"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return True
        presence_key = f"{key}_present"
        if isinstance(candidate.get(presence_key), bool) and candidate[presence_key]:
            return True
    return False


def _protocol_write_target_available(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    has_protocol_effect: bool,
) -> bool:
    explicit = request_payload.get("protocol_write_target_available")
    if isinstance(explicit, bool):
        return explicit
    authority = _dict_or_empty(response_payload.get("protocol_write_authority"))
    if isinstance(authority.get("target_available"), bool):
        return bool(authority.get("target_available"))
    candidate = _dict_or_empty(response_payload.get("protocol_write_candidate"))
    if isinstance(candidate.get("target_available"), bool):
        return bool(candidate.get("target_available"))
    if has_protocol_effect:
        return True
    return bool(
        str(candidate.get("protocol_id") or "").strip()
        and str(candidate.get("protocol_kind") or "").strip()
    )


def _effect_write_sources(write_ledger: WriteLedgerPlan) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    for entry in write_ledger.entries:
        if entry.category in NO_WRITE_LEDGER_CATEGORIES:
            continue
        sources.append(
            _write_source(
                source="existing_write_effect",
                field_path=",".join(entry.field_paths),
                kind=_effect_write_kind(entry),
                action=entry.operation or entry.category,
            )
        )
    return tuple(_dedupe_write_sources(sources))


def _write_source(*, source: str, field_path: str, kind: str, action: str | None) -> dict[str, Any]:
    return {
        "source": source,
        "field_path": field_path,
        "kind": kind,
        "action": action,
    }


def _dedupe_write_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str | None]] = set()
    deduped: list[dict[str, Any]] = []
    for source in sources:
        key = (
            str(source.get("source") or ""),
            str(source.get("field_path") or ""),
            str(source.get("kind") or ""),
            _optional_str(source.get("action")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _control_panel_write_kind(action_type: str) -> str | None:
    normalized = action_type.strip().lower()
    return {
        "draft_whiteboard": "whiteboard_draft",
        "save_whiteboard": "artifact_save",
        "publish_artifact": "artifact_publish",
        "remember": "memory_write",
        "create_memory": "memory_write",
        "memory_write": "memory_write",
        "save_memory": "memory_write",
        "learn": "concept_write",
        "conceptualize": "concept_write",
        "create_concept": "concept_write",
        "create_revision": "concept_write",
        "revise_concept": "concept_write",
        "concept_write": "concept_write",
        "save_concept": "concept_write",
        "upsert_concept": "concept_write",
        "protocol_write": "protocol_write",
        "upsert_protocol": "protocol_write",
        "update_protocol": "protocol_write",
        "create_artifact": "artifact_save",
    }.get(normalized)


def _semantic_write_kind(action_type: str) -> str | None:
    normalized = action_type.strip().lower()
    return {
        "artifact_save": "artifact_save",
        "artifact_publish": "artifact_publish",
        "save": "artifact_save",
        "publish": "artifact_publish",
        "save_whiteboard": "artifact_save",
        "publish_artifact": "artifact_publish",
        "remember": "memory_write",
        "create_memory": "memory_write",
        "memory_write": "memory_write",
        "save_memory": "memory_write",
        "learn": "concept_write",
        "conceptualize": "concept_write",
        "create_concept": "concept_write",
        "create_revision": "concept_write",
        "revise_concept": "concept_write",
        "concept_write": "concept_write",
        "save_concept": "concept_write",
        "upsert_concept": "concept_write",
        "protocol_write": "protocol_write",
        "upsert_protocol": "protocol_write",
        "update_protocol": "protocol_write",
        "create_artifact": "artifact_save",
    }.get(normalized)


def _write_intent_kind(kind: str) -> str | None:
    return {
        "whiteboard_draft": "whiteboard_draft",
        "whiteboard_offer": "whiteboard_offer",
        "scenario_branching": "scenario_branching",
        "artifact_action_proposal": "artifact_action_proposal",
    }.get(kind)


def _effect_write_kind(entry: WriteLedgerEntry) -> str:
    if entry.category == "artifact_save_or_promotion":
        operation = str(entry.operation or "").strip().lower()
        if "promote" in operation or "publish" in operation:
            return "artifact_publish"
        return "artifact_save"
    if entry.category == "concept_write":
        return "protocol_write" if str(entry.target_kind or "").strip().lower() == "protocol" else "concept_write"
    if entry.category == "memory_write":
        return "memory_write"
    if entry.category in {"proposed_calendar_task_mutation", "accepted_calendar_task_mutation"}:
        return "calendar_task_mutation"
    if entry.category == "pending_whiteboard_draft":
        return "whiteboard_draft"
    if entry.category == "pending_whiteboard_offer":
        return "whiteboard_offer"
    if entry.category == "draft_snapshot_workspace_update":
        return "whiteboard_draft"
    return entry.category


def _write_projection_agreement(
    *,
    intended_kinds: tuple[str, ...],
    actual_categories: tuple[str, ...],
    has_structured_sources: bool,
    has_effect_sources: bool,
) -> str:
    if not intended_kinds and not actual_categories:
        return "no_write"
    if actual_categories and not has_structured_sources:
        return "effect_without_explicit_intent" if has_effect_sources else "missing_intent"
    if intended_kinds and not actual_categories:
        return "intent_without_effect"
    if any(_write_kind_matches_category(kind, category) for kind in intended_kinds for category in actual_categories):
        return "aligned"
    return "mismatch"


def _write_kind_matches_category(kind: str, category: str) -> bool:
    if kind in {"artifact_save", "artifact_publish"}:
        return category == "artifact_save_or_promotion"
    if kind in {"concept_write", "protocol_write"}:
        return category == "concept_write"
    if kind == "memory_write":
        return category == "memory_write"
    if kind in {"whiteboard_draft", "whiteboard_offer"}:
        return category in {
            "pending_whiteboard_offer",
            "pending_whiteboard_draft",
            "draft_snapshot_workspace_update",
            "artifact_save_or_promotion",
        }
    if kind == "artifact_action_proposal":
        return category in {"proposed_calendar_task_mutation", "artifact_save_or_promotion"}
    if kind == "calendar_task_mutation":
        return category in {"proposed_calendar_task_mutation", "accepted_calendar_task_mutation"}
    if kind == "scenario_branching":
        return category in {"artifact_save_or_promotion", "draft_snapshot_workspace_update"}
    return kind == category


def _write_projection_compatibility(response_payload: dict[str, Any]) -> dict[str, Any]:
    invocation = _dict_or_empty(response_payload.get("surface_invocation"))
    return {
        "surface_invocation_intent": _optional_str(invocation.get("intent")),
        "surface_invocation_write_behavior": _normalized_write_behavior(invocation),
        "surface_invocation_has_write_intent": isinstance(invocation.get("write_intent"), dict),
        "surface_invocation_has_write_effects": isinstance(invocation.get("write_effects"), list),
    }


def _surface_intent_for_write_projection(projected_kind: str | None, legacy_intent: str | None) -> str | None:
    if not legacy_intent or legacy_intent in {"general", "general_chat", "chat_only"}:
        return projected_kind
    return None


def _surface_write_behavior_for_projection(
    projection: WriteProjectionPlan,
    legacy_write_behavior: str,
) -> str:
    if legacy_write_behavior != "none":
        return legacy_write_behavior
    if projection.actual_write_effect_count <= 0:
        return legacy_write_behavior
    if projection.intended_write_kind in {
        "artifact_save",
        "artifact_publish",
        "memory_write",
        "concept_write",
        "protocol_write",
    }:
        return "committed_write"
    return legacy_write_behavior


def _payload_has_explicit_write_authority(
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    write_intent: WriteIntentPlan,
) -> bool:
    """Return whether finalized structured fields explicitly authorize writing.

    Ordinary graph/action payloads are not authority by themselves. The only
    finalized write effect treated as authority here is a protocol upsert,
    because that payload is produced by the protocol interpreter before the
    general meta-write path.
    """

    if _optional_str(request_payload.get("memory_intent")) == "remember":
        return True
    if _protocol_write_candidate_action(response_payload) is not None:
        return True
    interpretation = _dict_or_empty(response_payload.get("turn_interpretation"))
    control_panel = _dict_or_empty(interpretation.get("control_panel"))
    if _control_panel_action_types(control_panel).intersection(
        {
            "draft_whiteboard",
            "save_whiteboard",
            "publish_artifact",
            "remember",
            "create_memory",
            "memory_write",
            "save_memory",
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
            "protocol_write",
            "upsert_protocol",
            "update_protocol",
            "create_artifact",
        }
    ):
        return True
    semantic_policy = _dict_or_empty(response_payload.get("semantic_policy"))
    semantic_action = str(semantic_policy.get("semantic_action") or "").strip().lower()
    policy_action = str(semantic_policy.get("action_type") or "").strip().lower()
    if semantic_action in {
        "save",
        "publish",
        "remember",
        "create_memory",
        "memory_write",
        "save_memory",
        "learn",
        "conceptualize",
        "create_concept",
        "create_revision",
        "revise_concept",
        "concept_write",
        "save_concept",
        "upsert_concept",
        "protocol_write",
        "upsert_protocol",
        "update_protocol",
        "create_artifact",
        "artifact_save",
        "artifact_publish",
    }:
        return True
    if policy_action in {
        "save_whiteboard",
        "publish_artifact",
        "remember",
        "create_memory",
        "memory_write",
        "save_memory",
        "learn",
        "conceptualize",
        "create_concept",
        "create_revision",
        "revise_concept",
        "concept_write",
        "save_concept",
        "upsert_concept",
        "protocol_write",
        "upsert_protocol",
        "update_protocol",
        "create_artifact",
        "artifact_save",
        "artifact_publish",
    }:
        return True
    graph_action = _dict_or_empty(response_payload.get("graph_action"))
    created_record = _dict_or_empty(response_payload.get("created_record"))
    graph_action_type = str(graph_action.get("type") or graph_action.get("action") or "").strip()
    created_record_type = str(created_record.get("type") or created_record.get("source") or "").strip()
    if graph_action_type == "upsert_protocol" or created_record_type == "protocol":
        return True
    return bool(
        write_intent.explicit_user_intent
        and write_intent.kind in {"whiteboard_draft", "whiteboard_offer", "scenario_branching"}
    )


def _payload_has_openable_artifact_context(response_payload: dict[str, Any]) -> bool:
    for artifact in _list_of_dicts(response_payload.get("visible_artifacts")):
        kind = str(artifact.get("kind") or "").strip().lower()
        artifact_id = str(artifact.get("id") or "").strip()
        if kind in {"artifact", "whiteboard"} or _is_openable_resource_id(artifact_id):
            return True
    for resource in _list_of_dicts(response_payload.get("selected_attention_resources")):
        kind = str(resource.get("kind") or "").strip().lower()
        app = str(resource.get("app") or "").strip().lower()
        surface = str(resource.get("suggested_surface") or "").strip().lower()
        source = str(resource.get("source") or "").strip().lower()
        resource_id = str(resource.get("resource_id") or resource.get("id") or "").strip()
        if (
            kind in {"artifact", "whiteboard"}
            or app == "whiteboard"
            or surface == "whiteboard"
            or source == "artifact"
            or _is_openable_resource_id(resource_id)
        ):
            return True
    return False


def _navigator_selected_ids(navigator_selection: dict[str, Any] | None) -> set[str]:
    if not navigator_selection:
        return set()
    selected: set[str] = set()
    primary = _optional_str(navigator_selection.get("primary_resource_id"))
    if primary:
        selected.add(primary)
    selected_ids = navigator_selection.get("selected_ids")
    if isinstance(selected_ids, list):
        selected.update(str(item).strip() for item in selected_ids if str(item).strip())
    return selected


def _surface_target_resource_id(invocation: dict[str, Any]) -> str | None:
    return _optional_str(
        invocation.get("target_resource_id")
        or invocation.get("target_id")
        or invocation.get("resource_id")
    )


def _has_explicit_write_authority(
    route: RoutePlan,
    write_intent: WriteIntentPlan,
    semantic: SemanticPlan,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
) -> bool:
    if _optional_str((request_payload or {}).get("memory_intent")) == "remember":
        return True
    if _protocol_write_candidate_action(response_payload or {}) is not None:
        return True
    if write_intent.explicit_user_intent and write_intent.kind in {
        "whiteboard_draft",
        "whiteboard_offer",
        "scenario_branching",
    }:
        return True
    if _control_panel_action_types(route.control_panel).intersection(
        {
            "draft_whiteboard",
            "save_whiteboard",
            "publish_artifact",
            "remember",
            "create_memory",
            "memory_write",
            "save_memory",
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
            "protocol_write",
            "upsert_protocol",
            "update_protocol",
        }
    ):
        return True
    semantic_action = str(semantic.semantic_action or "").strip().lower()
    policy_action = str(semantic.policy_action_type or "").strip().lower()
    response_payload = response_payload or {}
    graph_action = _dict_or_empty(response_payload.get("graph_action"))
    created_record = _dict_or_empty(response_payload.get("created_record"))
    graph_action_type = str(graph_action.get("type") or graph_action.get("action") or "").strip()
    created_record_type = str(created_record.get("type") or created_record.get("source") or "").strip()
    if graph_action_type == "upsert_protocol" or created_record_type == "protocol":
        return True
    return bool(
        semantic_action
        in {
            "save",
            "publish",
            "remember",
            "create_memory",
            "memory_write",
            "save_memory",
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
            "protocol_write",
            "upsert_protocol",
            "update_protocol",
            "create_artifact",
            "artifact_save",
            "artifact_publish",
        }
        or policy_action
        in {
            "save_whiteboard",
            "publish_artifact",
            "remember",
            "create_memory",
            "memory_write",
            "save_memory",
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
            "protocol_write",
            "upsert_protocol",
            "update_protocol",
            "create_artifact",
            "artifact_save",
            "artifact_publish",
        }
    )


def _workspace_update_ledger_entry(workspace_update: dict[str, Any]) -> WriteLedgerEntry:
    status = _workspace_update_status(workspace_update)
    category = _workspace_update_category(status)
    return WriteLedgerEntry(
        category=category,
        field_paths=("workspace_update",),
        status=status,
        target_kind="whiteboard",
        target_id=_optional_str(workspace_update.get("workspace_id") or workspace_update.get("id")),
        operation=_optional_str(workspace_update.get("type") or workspace_update.get("operation")),
        requires_confirmation=None,
        committed=status in {"applied", "completed", "saved", "accepted"},
    )


def _workspace_update_category(status: str | None) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"offered", "offer", "pending_offer", "whiteboard_offer"}:
        return "pending_whiteboard_offer"
    if normalized in {"draft", "draft_ready", "draft_whiteboard", "pending", "pending_draft", "whiteboard_draft"}:
        return "pending_whiteboard_draft"
    return "draft_snapshot_workspace_update"


def _record_write_ledger_entry(
    *,
    graph_action: dict[str, Any] | None,
    created_record: dict[str, Any] | None,
) -> WriteLedgerEntry:
    category = _record_write_category(graph_action=graph_action, created_record=created_record)
    record = created_record or {}
    action = graph_action or {}
    field_paths: list[str] = []
    if graph_action is not None:
        field_paths.append("graph_action")
    if created_record is not None:
        field_paths.append("created_record")
    return WriteLedgerEntry(
        category=category,
        field_paths=tuple(field_paths),
        status=_optional_str(record.get("status") or action.get("status") or "committed"),
        target_kind=_optional_str(record.get("source") or record.get("type") or record.get("kind")),
        target_id=_optional_str(record.get("id") or action.get("record_id") or action.get("concept_id")),
        operation=_optional_str(action.get("type") or action.get("action")),
        requires_confirmation=None,
        committed=True,
    )


def _record_write_category(
    *,
    graph_action: dict[str, Any] | None,
    created_record: dict[str, Any] | None,
) -> str:
    record = created_record or {}
    action = graph_action or {}
    record_kind = str(
        record.get("source")
        or record.get("type")
        or record.get("kind")
        or record.get("record_type")
        or ""
    ).strip().lower()
    action_kind = str(action.get("type") or action.get("action") or "").strip().lower()
    record_id = str(record.get("id") or "").strip().lower()
    if record_kind in {"memory", "saved_note"} or action_kind in {"create_memory", "upsert_memory", "save_memory"}:
        return "memory_write"
    if (
        record_kind in {"artifact", "workspace", "whiteboard"}
        or bool(record.get("artifact_lifecycle"))
        or action_kind in {
            "save_workspace_iteration_artifact",
            "promote_workspace_to_artifact",
            "create_artifact",
            "publish_artifact",
        }
    ):
        return "artifact_save_or_promotion"
    if (
        record_kind in {"concept", "protocol"}
        or record_id.startswith("concept:")
        or action_kind
        in {
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "upsert_concept",
            "upsert_protocol",
            "save_concept",
        }
    ):
        return "concept_write"
    if action_kind.startswith(("calendar_", "task_")):
        return "accepted_calendar_task_mutation"
    return "concept_write"


def _artifact_action_ledger_entry(action: dict[str, Any], *, index: int) -> WriteLedgerEntry:
    artifact_kind = str(action.get("artifact_kind") or action.get("kind") or action.get("app") or "").strip().lower()
    status = str(action.get("status") or "").strip().lower()
    committed = status in {"accepted", "applied", "completed"}
    if artifact_kind in {"calendar", "task", "tasks"}:
        category = "accepted_calendar_task_mutation" if committed else "proposed_calendar_task_mutation"
    else:
        category = "artifact_save_or_promotion"
    requires_confirmation = action.get("requires_confirmation")
    return WriteLedgerEntry(
        category=category,
        field_paths=(f"artifact_actions[{index}]",),
        status=_optional_str(status),
        target_kind=artifact_kind or None,
        target_id=_optional_str(action.get("target_id") or action.get("artifact_id") or action.get("id")),
        operation=_optional_str(action.get("operation") or action.get("type") or action.get("intent")),
        requires_confirmation=requires_confirmation if isinstance(requires_confirmation, bool) else None,
        committed=committed,
    )


def _write_ledger_no_write_reason(
    *,
    entries: list[WriteLedgerEntry],
    write_intent: WriteIntentPlan,
    surface_action: dict[str, Any] | None,
    invocation: dict[str, Any],
) -> str | None:
    if any(entry.category not in NO_WRITE_LEDGER_CATEGORIES for entry in entries):
        return None
    intent = _optional_str(invocation.get("intent"))
    if surface_action is not None:
        return "close_visible_surface"
    if intent == "preserve_visible_surface":
        return "preserve_visible_surface"
    if write_intent.write_behavior == "open_only":
        return "open_only_ui_handoff"
    if intent in {"current_artifact_followup", "selected_material_question"}:
        return "artifact_qna_chat_first"
    return "no_write_effects"


def _dedupe(values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return tuple(ordered)


def _has_deletion_semantics(response_payload: dict[str, Any]) -> bool:
    workspace_update = _optional_dict(response_payload.get("workspace_update"))
    if workspace_update and _looks_delete_like(workspace_update.get("type") or workspace_update.get("status")):
        return True
    graph_action = _optional_dict(response_payload.get("graph_action"))
    if graph_action and _looks_delete_like(graph_action.get("action") or graph_action.get("type")):
        return True
    return any(
        _looks_delete_like(action.get("operation") or action.get("type") or action.get("intent"))
        for action in _list_of_dicts(response_payload.get("artifact_actions"))
    )


def _calendar_task_mutation_fields(response_payload: dict[str, Any]) -> list[str]:
    invocation = _dict_or_empty(response_payload.get("surface_invocation"))
    write_behavior = _normalized_write_behavior(invocation)
    warnings: list[str] = []
    for index, action in enumerate(_list_of_dicts(response_payload.get("artifact_actions"))):
        artifact_kind = str(action.get("artifact_kind") or action.get("kind") or action.get("app") or "").strip().lower()
        if artifact_kind not in {"calendar", "task", "tasks"}:
            continue
        status = str(action.get("status") or "").strip().lower()
        requires_confirmation = action.get("requires_confirmation")
        if write_behavior != "proposal_only" or status in {"accepted", "applied", "completed"} or requires_confirmation is False:
            warnings.append(f"artifact_actions[{index}]")
    return warnings


def _looks_delete_like(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"delete", "deleted", "remove", "removed", "cancel", "cancelled", "canceled"} or text.startswith(
        ("delete_", "remove_", "cancel_")
    )


def _validation_warning(code: str, message: str, fields: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warning",
        "message": message,
        "fields": fields,
    }


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
