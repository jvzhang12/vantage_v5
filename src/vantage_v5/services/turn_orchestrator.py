from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import logging
from typing import Any, Callable

from vantage_v5.services.artifact_actions import is_task_capture_request
from vantage_v5.services.attention import apply_attention_surface_selection
from vantage_v5.services.attention import attention_payload
from vantage_v5.services.attention import AttentionEngine
from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import ContextEngine
from vantage_v5.services.local_semantic_actions import LocalSemanticActionEngine
from vantage_v5.services.local_semantic_actions import LocalSemanticTurnContext
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.navigator import apply_control_panel_open_intent_fallback
from vantage_v5.services.protocol_engine import ProtocolEngine
from vantage_v5.services.semantic_frame import build_semantic_frame
from vantage_v5.services.semantic_policy import decide_semantic_policy
from vantage_v5.services.surface_invocation import build_surface_invocation
from vantage_v5.services.turn_plan import build_turn_plan_artifact_write_authority
from vantage_v5.services.turn_plan import build_turn_plan_draft_authority
from vantage_v5.services.turn_plan import build_turn_plan_surface_authority
from vantage_v5.services.turn_plan import TurnPlanExecutionPolicy
from vantage_v5.services.turn_payloads import assemble_local_turn_payload
from vantage_v5.services.turn_payloads import assemble_scenario_lab_fallback_payload
from vantage_v5.services.turn_payloads import assemble_service_turn_payload
from vantage_v5.services.turn_payloads import assemble_turn_interpretation_payload
from vantage_v5.services.turn_payloads import build_local_turn_parts
from vantage_v5.services.turn_payloads import LocalTurnBodyParts
from vantage_v5.services.turn_payloads import LocalTurnContext
from vantage_v5.services.turn_payloads import ScenarioLabFallbackParts
from vantage_v5.services.turn_payloads import ServiceTurnPayloadParts
from vantage_v5.services.turn_payloads import sanitize_public_attention_state_payload
from vantage_v5.services.turn_payloads import TurnInterpretationParts
from vantage_v5.services.turn_staging import build_turn_stage
from vantage_v5.services.turn_staging import initial_stage_progress
from vantage_v5.services.turn_staging import stage_progress_event
from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.workspaces import WorkspaceDocument


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TurnOrchestratorHooks:
    should_enter_scenario_lab: Callable[..., bool]


class TurnOrchestrator:
    def __init__(
        self,
        *,
        navigator_service: NavigatorService,
        context_engine: ContextEngine,
        protocol_engine: ProtocolEngine,
        local_semantic_actions: LocalSemanticActionEngine,
        whiteboard_routing: WhiteboardRoutingEngine,
        hooks: TurnOrchestratorHooks,
        attention_engine: AttentionEngine | None = None,
    ) -> None:
        self.navigator_service = navigator_service
        self.context_engine = context_engine
        self.protocol_engine = protocol_engine
        self.local_semantic_actions = local_semantic_actions
        self.whiteboard_routing = whiteboard_routing
        self.hooks = hooks
        self.attention_engine = attention_engine

    def run(self, request: ChatTurnRequestContext) -> dict[str, Any]:
        context = self.context_engine.prepare_turn_context(request)
        attention_turn = (
            self.attention_engine.prepare_turn(
                message=request.message,
                runtime=context.runtime,
                workspace=context.workspace,
                visible_artifacts=context.visible_artifacts,
            )
            if self.attention_engine is not None
            else None
        )
        attention_candidates = attention_turn.compact_candidates() if attention_turn is not None else []
        navigation = request.navigation
        if navigation is None:
            navigation = self.navigator_service.route_turn(
                user_message=request.message,
                history=request.history,
                workspace=context.workspace,
                requested_whiteboard_mode=request.whiteboard_mode,
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                selected_record_id=request.pinned_context_id,
                selected_record=context.pinned_context,
                pending_workspace_update=context.pending_workspace_update,
                continuity_context=context.continuity_context,
                visible_artifacts=context.visible_artifacts,
                attention_candidates=attention_candidates,
            )
        navigation = apply_control_panel_open_intent_fallback(
            navigation,
            user_message=request.message,
            attention_candidates=attention_candidates,
        )
        task_capture_consumes_memory = _task_capture_consumes_memory_action(
            request.message,
            requested_memory_intent=request.memory_intent,
        )
        if task_capture_consumes_memory:
            navigation = _without_memory_control_actions(navigation)
        attention_selection = None
        selected_attention_resources = ()
        if attention_turn is not None:
            attention_selection, selected_attention_resources = attention_turn.select(
                navigation.attention_selection,
            )
        selected_attention_payload = [resource.to_dict() for resource in selected_attention_resources]
        model_visible_artifacts = _visible_artifacts_with_current_workspace(
            context.visible_artifacts,
            workspace=context.workspace,
            workspace_scope=context.normalized_workspace_scope,
        )
        surface_invocation = build_surface_invocation(
            user_message=request.message,
            requested_whiteboard_mode=request.whiteboard_mode,
            navigation=navigation,
            visible_artifacts=model_visible_artifacts,
        )
        routed_whiteboard_mode = self.whiteboard_routing.resolve_whiteboard_mode(
            request.whiteboard_mode,
            navigation,
            user_message=request.message,
            workspace=context.workspace,
        )
        resolved_whiteboard_mode = surface_invocation.resolved_whiteboard_mode(
            requested_mode=request.whiteboard_mode,
            current_mode=routed_whiteboard_mode,
        )
        surface_invocation_payload = apply_attention_surface_selection(
            surface_invocation.to_dict(),
            attention_selection,
            selected_resources=selected_attention_resources,
        )
        attention_state_payload = attention_payload(
            turn=attention_turn,
            selection=attention_selection,
            selected_resources=selected_attention_resources,
        )
        public_attention_state_payload = sanitize_public_attention_state_payload(attention_state_payload)
        surface_authority = build_turn_plan_surface_authority(
            response_payload={
                **attention_state_payload,
                "surface_invocation": surface_invocation_payload,
            }
        )
        suppress_auto_graph_writes = False
        if surface_authority.is_preserve:
            suppress_auto_graph_writes = True
            resolved_whiteboard_mode = "chat"
            surface_invocation_payload["whiteboard_mode"] = "chat"
        elif surface_authority.is_whiteboard_open_only:
            suppress_auto_graph_writes = True
            if (
                resolved_whiteboard_mode == "draft"
                and (
                    self.whiteboard_routing.is_explicit_whiteboard_draft_request(request.message)
                    or self.whiteboard_routing.should_continue_current_whiteboard_draft(
                        request.message,
                        context.workspace,
                    )
                )
            ):
                suppress_auto_graph_writes = False
                surface_invocation_payload["write_behavior"] = "draft_only"
                surface_invocation_payload["whiteboard_mode"] = "draft"
            else:
                resolved_whiteboard_mode = "chat"
                surface_invocation_payload["whiteboard_mode"] = "chat"
        surface_invocation_payload["resolved_whiteboard_mode"] = (
            resolved_whiteboard_mode if navigation.mode == "chat" else None
        )
        surface_authority = build_turn_plan_surface_authority(
            response_payload={
                **attention_state_payload,
                "surface_invocation": surface_invocation_payload,
            }
        )
        resolved_protocols = self.protocol_engine.resolve_for_turn(
            navigation=navigation,
            request=request,
            context=context,
        )
        applied_protocol_kinds = resolved_protocols.applied_protocol_kinds
        semantic_frame_model = build_semantic_frame(
            user_message=request.message,
            navigation=navigation,
            requested_whiteboard_mode=request.whiteboard_mode,
            resolved_whiteboard_mode=resolved_whiteboard_mode if navigation.mode == "chat" else None,
            whiteboard_entry_mode=context.whiteboard_entry_mode,
            workspace=context.workspace,
            workspace_scope=context.normalized_workspace_scope,
            pinned_context_id=request.pinned_context_id,
            pinned_context=context.pinned_context,
            pending_workspace_update=context.pending_workspace_update,
        )
        semantic_frame = semantic_frame_model.to_dict()
        semantic_policy = decide_semantic_policy(
            semantic_frame_model,
            context=self.local_semantic_actions.policy_context(
                semantic_frame=semantic_frame_model,
                session=context.session,
                workspace=context.workspace,
                workspace_scope=context.normalized_workspace_scope,
                pinned_context=context.pinned_context,
                pending_workspace_update=context.pending_workspace_update,
                user_message=request.message,
            ),
        ).to_dict()
        effective_memory_intent = _effective_memory_intent(
            request.memory_intent,
            navigation=navigation,
            semantic_policy=semantic_policy,
            task_capture_consumes_memory=task_capture_consumes_memory,
        )
        turn_interpretation_parts = TurnInterpretationParts(
            navigation=navigation,
            requested_whiteboard_mode=request.whiteboard_mode,
            resolved_whiteboard_mode=resolved_whiteboard_mode,
            whiteboard_entry_mode=context.whiteboard_entry_mode,
            explicit_whiteboard_draft_request=self.whiteboard_routing.is_explicit_whiteboard_draft_request(
                request.message
            ),
            whiteboard_mode_source="surface_invocation"
            if resolved_whiteboard_mode != routed_whiteboard_mode
            else None,
        )
        surface_authority = build_turn_plan_surface_authority(
            response_payload={
                **attention_state_payload,
                "surface_invocation": surface_invocation_payload,
                "turn_interpretation": assemble_turn_interpretation_payload(turn_interpretation_parts),
                "semantic_policy": semantic_policy,
            },
            request_payload={"message": request.message, "memory_intent": effective_memory_intent},
        )
        workspace_has_content = bool(context.workspace.content.strip())
        artifact_write_authority = build_turn_plan_artifact_write_authority(
            response_payload={
                **attention_state_payload,
                "surface_invocation": surface_invocation_payload,
                "turn_interpretation": assemble_turn_interpretation_payload(turn_interpretation_parts),
                "semantic_policy": semantic_policy,
            },
            request_payload={
                "message": request.message,
                "memory_intent": effective_memory_intent,
                "workspace_scope": context.normalized_workspace_scope,
                "workspace_has_content": workspace_has_content,
                "artifact_write_target_available": context.normalized_workspace_scope != "excluded"
                and workspace_has_content,
            },
        )
        draft_authority = build_turn_plan_draft_authority(
            response_payload={
                **attention_state_payload,
                "surface_invocation": surface_invocation_payload,
                "turn_interpretation": assemble_turn_interpretation_payload(turn_interpretation_parts),
                "semantic_policy": semantic_policy,
            },
            request_payload={
                "message": request.message,
                "memory_intent": effective_memory_intent,
                "whiteboard_mode": request.whiteboard_mode,
            },
        )
        execution_policy = TurnPlanExecutionPolicy(
            surface_authority=surface_authority,
            artifact_write_authority=artifact_write_authority,
            draft_authority=draft_authority,
        )
        turn_stage = build_turn_stage(
            navigation_mode=navigation.mode,
            whiteboard_mode=resolved_whiteboard_mode if navigation.mode == "chat" else "chat",
            public_summary=navigation.reason,
        )
        close_surface_action = surface_authority.surface_action if surface_authority.is_close else None
        if close_surface_action is not None:
            assistant_message = _close_surface_assistant_message(close_surface_action)
            if execution_policy.blocks_denied_draft_update:
                assistant_message = (
                    f"{assistant_message} "
                    f"{_denied_whiteboard_draft_sentence(draft_authority)}"
                )
            if _has_structured_concept_write_action(navigation, semantic_policy):
                assistant_message = f"{assistant_message} {_denied_concept_write_sentence()}"
            local_context = LocalTurnContext(
                user_message=request.message,
                history=request.history,
                workspace=context.workspace,
                workspace_scope=context.normalized_workspace_scope,
                runtime_scope=context.runtime["scope"],
                transient_workspace=context.transient_workspace,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                experiment=self.local_semantic_actions.session_info(context.session),
                surface_invocation=surface_invocation_payload,
            )
            payload = assemble_local_turn_payload(
                build_local_turn_parts(
                    local_context,
                    turn_body=LocalTurnBodyParts(
                        assistant_message=assistant_message,
                        mode="local_action",
                    ),
                    turn_interpretation=turn_interpretation_parts,
                    turn_stage=turn_stage,
                )
            )
            payload.update(public_attention_state_payload)
            return payload
        if execution_policy.blocks_denied_draft_update:
            local_context = LocalTurnContext(
                user_message=request.message,
                history=request.history,
                workspace=context.workspace,
                workspace_scope=context.normalized_workspace_scope,
                runtime_scope=context.runtime["scope"],
                transient_workspace=context.transient_workspace,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                experiment=self.local_semantic_actions.session_info(context.session),
                surface_invocation=surface_invocation_payload,
            )
            payload = assemble_local_turn_payload(
                build_local_turn_parts(
                    local_context,
                    turn_body=LocalTurnBodyParts(
                        assistant_message=_denied_whiteboard_draft_assistant_message(
                            surface_authority,
                            draft_authority,
                        ),
                        mode="local_action",
                    ),
                    turn_interpretation=turn_interpretation_parts,
                    turn_stage=turn_stage,
                )
            )
            payload.update(public_attention_state_payload)
            return payload
        local_semantic_parts = None
        local_semantic_write_action = _semantic_policy_has_local_write_action(semantic_policy)
        local_semantic_clarification = _semantic_policy_should_clarify(semantic_policy)
        local_semantic_blocked_by_surface = execution_policy.blocks_local_semantic_write_action(
            local_semantic_write_action
        )
        local_semantic_blocked_by_artifact_authority = (
            execution_policy.blocks_local_semantic_artifact_write_action(
                has_write_action=local_semantic_write_action,
                has_clarification=local_semantic_clarification,
            )
        )
        concept_write_blocked_by_hard_no_write = execution_policy.blocks_structured_concept_write(
            _has_structured_concept_write_action(navigation, semantic_policy)
        )
        if local_semantic_blocked_by_artifact_authority and execution_policy.blocks_denied_artifact_write:
            local_context = LocalTurnContext(
                user_message=request.message,
                history=request.history,
                workspace=context.workspace,
                workspace_scope=context.normalized_workspace_scope,
                runtime_scope=context.runtime["scope"],
                transient_workspace=context.transient_workspace,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                experiment=self.local_semantic_actions.session_info(context.session),
                surface_invocation=surface_invocation_payload,
            )
            payload = assemble_local_turn_payload(
                build_local_turn_parts(
                    local_context,
                    turn_body=LocalTurnBodyParts(
                        assistant_message=_denied_artifact_write_assistant_message(
                            surface_authority,
                            artifact_write_authority,
                        ),
                        mode="local_action",
                    ),
                    turn_interpretation=turn_interpretation_parts,
                    turn_stage=turn_stage,
                )
            )
            payload.update(public_attention_state_payload)
            return payload
        if concept_write_blocked_by_hard_no_write:
            local_context = LocalTurnContext(
                user_message=request.message,
                history=request.history,
                workspace=context.workspace,
                workspace_scope=context.normalized_workspace_scope,
                runtime_scope=context.runtime["scope"],
                transient_workspace=context.transient_workspace,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                experiment=self.local_semantic_actions.session_info(context.session),
                surface_invocation=surface_invocation_payload,
            )
            payload = assemble_local_turn_payload(
                build_local_turn_parts(
                    local_context,
                    turn_body=LocalTurnBodyParts(
                        assistant_message=_denied_concept_write_assistant_message(surface_authority),
                        mode="local_action",
                    ),
                    turn_interpretation=turn_interpretation_parts,
                    turn_stage=turn_stage,
                )
            )
            payload.update(public_attention_state_payload)
            return payload
        if not (local_semantic_blocked_by_surface or local_semantic_blocked_by_artifact_authority):
            local_semantic_parts = self.local_semantic_actions.build_turn_parts(
                LocalSemanticTurnContext(
                    runtime=context.runtime,
                    session=context.session,
                    message=request.message,
                    history=request.history,
                    workspace=context.workspace,
                    workspace_scope=context.normalized_workspace_scope,
                    transient_workspace=context.transient_workspace,
                    semantic_frame=semantic_frame,
                    semantic_policy=semantic_policy,
                    pinned_context_id=request.pinned_context_id,
                    pinned_context=context.pinned_context,
                )
            )
        if local_semantic_parts is not None:
            payload = assemble_local_turn_payload(
                replace(
                    local_semantic_parts,
                    turn_interpretation=turn_interpretation_parts,
                    surface_invocation=surface_invocation_payload,
                )
            )
            payload.update(public_attention_state_payload)
            return payload

        if self.hooks.should_enter_scenario_lab(navigation):
            try:
                turn = context.runtime["scenario_lab_service"].run(
                    message=request.message,
                    workspace=context.workspace,
                    history=request.history,
                    navigation=navigation,
                    selected_record_id=request.pinned_context_id,
                    pending_workspace_update=context.pending_workspace_update,
                    visible_artifacts=model_visible_artifacts,
                    applied_protocol_kinds=applied_protocol_kinds,
                )
            except Exception as exc:
                logger.exception("Scenario Lab request failed unexpectedly. Falling back to normal chat.")
                return self._scenario_lab_fallback_payload(
                    runtime=context.runtime,
                    session=context.session,
                    request=request,
                    workspace=context.workspace,
                    normalized_workspace_scope=context.normalized_workspace_scope,
                    transient_workspace=context.transient_workspace,
                    navigation=navigation,
                    resolved_whiteboard_mode=resolved_whiteboard_mode,
                    semantic_frame=semantic_frame,
                    semantic_policy=semantic_policy,
                    pinned_context=context.pinned_context,
                    pending_workspace_update=context.pending_workspace_update,
                    applied_protocol_kinds=applied_protocol_kinds,
                    turn_interpretation=turn_interpretation_parts,
                    surface_invocation=surface_invocation_payload,
                    error=exc,
                    attention_state_payload=attention_state_payload,
                )
            turn.turn_stage = turn_stage.to_dict()
            turn.stage_progress = [
                *initial_stage_progress(turn_stage),
                stage_progress_event(
                    "stage_accept",
                    "Accepted response",
                    message="Scenario Lab completed and saved the comparison outputs.",
                ),
            ]
            turn.stage_audit = {"accepted": True, "status": "accepted", "issues": [], "retry_instruction": ""}
        else:
            turn = context.runtime["chat_service"].reply(
                message=request.message,
                workspace=context.workspace,
                history=request.history,
                memory_intent=effective_memory_intent,
                selected_record_id=request.pinned_context_id,
                whiteboard_mode=resolved_whiteboard_mode,
                preserve_selected_record=(
                    navigation.preserve_pinned_context
                    if navigation.preserve_pinned_context is not None
                    else navigation.preserve_selected_record
                ),
                selected_record_reason=navigation.pinned_context_reason or navigation.selected_record_reason,
                pending_workspace_update=context.pending_workspace_update,
                workspace_is_transient=context.transient_workspace,
                workspace_scope=context.normalized_workspace_scope,
                visible_artifacts=model_visible_artifacts,
                selected_attention_resources=selected_attention_payload,
                app_capabilities=context.app_capabilities,
                applied_protocol_kinds=applied_protocol_kinds,
                turn_stage=turn_stage,
                **execution_policy.chat_reply_kwargs(),
                surface_invocation=surface_invocation_payload,
                turn_interpretation=assemble_turn_interpretation_payload(turn_interpretation_parts),
                semantic_policy=semantic_policy,
            )

        payload = assemble_service_turn_payload(
            ServiceTurnPayloadParts(
                turn_body=turn.to_body_parts(),
                pinned_context_id=request.pinned_context_id,
                pinned_context=context.pinned_context,
                turn_interpretation=turn_interpretation_parts,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                workspace=context.workspace,
                runtime_scope=context.runtime["scope"],
                workspace_scope=context.normalized_workspace_scope,
                transient_workspace=context.transient_workspace,
                experiment=self.local_semantic_actions.session_info(context.session),
                surface_invocation=surface_invocation_payload,
            )
        )
        payload.update(public_attention_state_payload)
        trace_path = getattr(turn, "trace_path", None)
        if trace_path:
            payload["_turn_trace_path"] = trace_path
        return payload

    def _scenario_lab_fallback_payload(
        self,
        *,
        runtime: dict[str, Any],
        session: Any,
        request: ChatTurnRequestContext,
        workspace: WorkspaceDocument,
        normalized_workspace_scope: str,
        transient_workspace: bool,
        navigation: NavigationDecision,
        resolved_whiteboard_mode: str,
        semantic_frame: dict[str, Any],
        semantic_policy: dict[str, Any],
        pinned_context: dict[str, Any] | None,
        pending_workspace_update: dict[str, Any] | None,
        applied_protocol_kinds: list[str],
        turn_interpretation: TurnInterpretationParts,
        surface_invocation: dict[str, Any],
        error: Exception,
        attention_state_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        authority_payload = {
            "surface_invocation": surface_invocation,
            "turn_interpretation": assemble_turn_interpretation_payload(turn_interpretation),
            "semantic_policy": semantic_policy,
        }
        if attention_state_payload:
            authority_payload.update(attention_state_payload)
        surface_authority = build_turn_plan_surface_authority(
            response_payload=authority_payload,
            request_payload={"message": request.message, "memory_intent": request.memory_intent},
        )
        draft_authority = build_turn_plan_draft_authority(
            response_payload=authority_payload,
            request_payload={
                "message": request.message,
                "memory_intent": request.memory_intent,
                "whiteboard_mode": request.whiteboard_mode,
            },
        )
        execution_policy = TurnPlanExecutionPolicy(
            surface_authority=surface_authority,
            draft_authority=draft_authority,
        )
        turn = runtime["chat_service"].reply(
            message=request.message,
            workspace=workspace,
            history=request.history,
            memory_intent=request.memory_intent,
            selected_record_id=request.pinned_context_id,
            whiteboard_mode=resolved_whiteboard_mode,
            preserve_selected_record=(
                navigation.preserve_pinned_context
                if navigation.preserve_pinned_context is not None
                else navigation.preserve_selected_record
            ),
            selected_record_reason=navigation.pinned_context_reason or navigation.selected_record_reason,
            pending_workspace_update=pending_workspace_update,
            workspace_is_transient=transient_workspace,
            workspace_scope=normalized_workspace_scope,
            visible_artifacts=request.visible_artifacts,
            selected_attention_resources=(
                attention_state_payload.get("selected_attention_resources")
                if isinstance(attention_state_payload, dict)
                else []
            ),
            applied_protocol_kinds=applied_protocol_kinds,
            turn_stage=build_turn_stage(
                navigation_mode="chat",
                whiteboard_mode=resolved_whiteboard_mode,
                public_summary="Scenario Lab fell back to a chat response.",
            ),
            **execution_policy.chat_reply_kwargs(),
            surface_invocation=surface_invocation,
            turn_interpretation=assemble_turn_interpretation_payload(turn_interpretation),
            semantic_policy=semantic_policy,
        )
        payload = assemble_scenario_lab_fallback_payload(
            ScenarioLabFallbackParts(
                turn_body=turn.to_body_parts(),
                navigation=navigation.to_dict(),
                comparison_question=navigation.comparison_question,
                reason=navigation.reason,
                error_type=type(error).__name__,
                error_message=_safe_scenario_lab_error_message(error),
                pinned_context_id=request.pinned_context_id,
                pinned_context=pinned_context,
                turn_interpretation=turn_interpretation,
                semantic_frame=semantic_frame,
                semantic_policy=semantic_policy,
                workspace=workspace,
                runtime_scope=runtime["scope"],
                workspace_scope=normalized_workspace_scope,
                transient_workspace=transient_workspace,
                experiment=self.local_semantic_actions.session_info(session),
                surface_invocation=surface_invocation,
            )
        )
        if attention_state_payload:
            payload.update(sanitize_public_attention_state_payload(attention_state_payload))
        trace_path = getattr(turn, "trace_path", None)
        if trace_path:
            payload["_turn_trace_path"] = trace_path
        return payload


def _close_surface_assistant_message(action: dict[str, Any]) -> str:
    if action.get("status") == "no_visible_surface":
        return "I don't see a visible surface to close."
    title = str(action.get("title") or "").strip()
    target = str(action.get("target") or action.get("target_kind") or "surface").strip().replace("_", " ")
    if title:
        return f"Closed {title} from view."
    return f"Closed the {target} from view."


def _visible_artifacts_with_current_workspace(
    visible_artifacts: list[dict[str, Any]],
    *,
    workspace: WorkspaceDocument,
    workspace_scope: str,
) -> list[dict[str, Any]]:
    artifacts = [dict(artifact) for artifact in visible_artifacts if isinstance(artifact, dict)]
    if workspace_scope == "excluded" or not workspace.content.strip():
        return artifacts
    if any(_visible_artifact_is_whiteboard_like(artifact) for artifact in artifacts):
        return artifacts
    artifacts.append(
        {
            "id": f"workspace:{workspace.workspace_id}",
            "kind": "whiteboard",
            "title": workspace.title or "Whiteboard",
            "summary": f"Visible whiteboard: {workspace.title or 'Whiteboard'}.",
            "content": workspace.content,
            "workspace_id": workspace.workspace_id,
        }
    )
    return artifacts


def _visible_artifact_is_whiteboard_like(artifact: dict[str, Any]) -> bool:
    kind = str(artifact.get("kind") or "").strip().lower()
    if kind in {"whiteboard", "artifact"}:
        return True
    item_id = str(artifact.get("id") or "").strip().lower()
    return item_id.startswith("artifact:") or item_id.startswith("workspace:")


def _semantic_policy_has_local_write_action(policy: dict[str, Any]) -> bool:
    return any(
        str(value or "").strip().lower() in {"artifact_save", "artifact_publish"}
        for value in (policy.get("action_type"), policy.get("semantic_action"))
    )


def _has_structured_concept_write_action(
    navigation: NavigationDecision,
    semantic_policy: dict[str, Any],
) -> bool:
    return _navigation_has_concept_action(navigation) or _semantic_policy_has_concept_action(semantic_policy)


def _navigation_has_concept_action(navigation: NavigationDecision) -> bool:
    control_panel = navigation.control_panel if isinstance(navigation.control_panel, dict) else {}
    actions = control_panel.get("actions")
    if not isinstance(actions, list):
        return False
    return any(
        isinstance(action, dict)
        and str(action.get("type") or action.get("action") or "").strip().lower()
        in {
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
        }
        for action in actions
    )


def _semantic_policy_has_concept_action(policy: dict[str, Any]) -> bool:
    return any(
        str(value or "").strip().lower()
        in {
            "learn",
            "conceptualize",
            "create_concept",
            "create_revision",
            "revise_concept",
            "concept_write",
            "save_concept",
            "upsert_concept",
        }
        for value in (policy.get("action_type"), policy.get("semantic_action"))
    )


def _semantic_policy_should_clarify(policy: dict[str, Any]) -> bool:
    return bool(policy.get("should_clarify") or policy.get("needs_clarification"))


def _effective_memory_intent(
    requested_memory_intent: str,
    *,
    navigation: NavigationDecision,
    semantic_policy: dict[str, Any],
    task_capture_consumes_memory: bool = False,
) -> str:
    normalized = str(requested_memory_intent or "auto").strip().lower()
    if normalized in {"remember", "skip", "dont_save"}:
        return normalized
    if task_capture_consumes_memory:
        return normalized or "auto"
    if _navigation_has_memory_action(navigation) or _semantic_policy_has_memory_action(semantic_policy):
        return "remember"
    return normalized or "auto"


def _task_capture_consumes_memory_action(message: str, *, requested_memory_intent: str | None) -> bool:
    normalized = str(requested_memory_intent or "auto").strip().lower()
    if normalized == "remember":
        return False
    return is_task_capture_request(message)


def _without_memory_control_actions(navigation: NavigationDecision) -> NavigationDecision:
    control_panel = navigation.control_panel if isinstance(navigation.control_panel, dict) else {}
    actions = control_panel.get("actions")
    if not isinstance(actions, list):
        return navigation
    filtered_actions = [
        action
        for action in actions
        if not (
            isinstance(action, dict)
            and str(action.get("type") or action.get("action") or "").strip().lower()
            in {"remember", "memory_write", "save_memory", "create_memory"}
        )
    ]
    if len(filtered_actions) == len(actions):
        return navigation
    return replace(
        navigation,
        control_panel={
            **control_panel,
            "actions": filtered_actions,
            "memory_action_suppressed_by": "task_capture_operational_proposal",
        },
    )


def _navigation_has_memory_action(navigation: NavigationDecision) -> bool:
    control_panel = navigation.control_panel if isinstance(navigation.control_panel, dict) else {}
    actions = control_panel.get("actions")
    if not isinstance(actions, list):
        return False
    return any(
        isinstance(action, dict)
        and str(action.get("type") or "").strip().lower() in {"remember", "memory_write", "save_memory"}
        for action in actions
    )


def _semantic_policy_has_memory_action(policy: dict[str, Any]) -> bool:
    action_type = str(policy.get("action_type") or policy.get("semantic_action") or "").strip().lower()
    return action_type in {"remember", "memory_write", "save_memory", "create_memory"}


def _denied_artifact_write_assistant_message(surface_authority: Any, artifact_write_authority: Any) -> str:
    denied_sentence = _denied_artifact_write_sentence(str(artifact_write_authority.action or "artifact_save"))
    reason = str(artifact_write_authority.denied_reason or "")
    if reason == "preserve_visible_surface":
        target = _surface_target_label(surface_authority)
        return f"I kept the {target} open. {denied_sentence}"
    if reason == "open_only_ui_handoff":
        return f"I opened the selected material in the whiteboard. {denied_sentence}"
    if reason == "close_visible_surface":
        return f"Closed the {_surface_target_label(surface_authority)} from view. {denied_sentence}"
    return denied_sentence


def _denied_artifact_write_sentence(action: str) -> str:
    if action == "artifact_publish":
        return "I did not publish it."
    return "I did not save it."


def _denied_concept_write_assistant_message(surface_authority: Any) -> str:
    reason = str(surface_authority.no_write_reason or "")
    if reason == "preserve_visible_surface":
        target = _surface_target_label(surface_authority)
        return f"I kept the {target} open. {_denied_concept_write_sentence()}"
    if reason == "open_only_ui_handoff":
        return f"I opened the selected material in the whiteboard. {_denied_concept_write_sentence()}"
    if reason == "close_visible_surface":
        return f"Closed the {_surface_target_label(surface_authority)} from view. {_denied_concept_write_sentence()}"
    return _denied_concept_write_sentence()


def _denied_concept_write_sentence() -> str:
    return "I did not learn it as a concept."


def _denied_whiteboard_draft_assistant_message(surface_authority: Any, draft_authority: Any) -> str:
    denied_sentence = _denied_whiteboard_draft_sentence(draft_authority)
    reason = str(draft_authority.denied_reason or surface_authority.no_write_reason or "")
    if reason == "preserve_visible_surface":
        target = _surface_target_label(surface_authority)
        return f"I kept the {target} open. {denied_sentence}"
    if reason == "open_only_ui_handoff":
        return f"I opened the selected material in the whiteboard. {denied_sentence}"
    if reason == "close_visible_surface":
        return f"Closed the {_surface_target_label(surface_authority)} from view. {denied_sentence}"
    return denied_sentence


def _denied_whiteboard_draft_sentence(draft_authority: Any) -> str:
    if str(getattr(draft_authority, "action", "") or "") == "whiteboard_offer":
        return "I did not offer a new whiteboard draft."
    return "I did not draft or update the whiteboard."


def _surface_target_label(surface_authority: Any) -> str:
    raw = (
        getattr(surface_authority.ui_surface_action, "target_resource_kind", None)
        or getattr(surface_authority.ui_surface_action, "surface", None)
        or "surface"
    )
    label = str(raw).strip().replace("_", " ")
    if label in {"none", ""}:
        return "surface"
    if label in {"calendar day", "calendar week"}:
        return "calendar"
    if label == "today briefing":
        return "Today"
    return label


def _safe_scenario_lab_error_message(error: Exception) -> str:
    raw = str(error)
    if "rate limit" in raw.lower() or "openai" in type(error).__module__.lower():
        return "Scenario Lab could not complete because the model provider was temporarily unavailable. The turn stayed in chat so you can retry or continue from here."
    return "Scenario Lab could not complete this turn. The turn stayed in chat so you can retry or continue from here."
