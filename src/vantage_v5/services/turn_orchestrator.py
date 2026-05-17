from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import logging
from typing import Any, Callable

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
from vantage_v5.services.turn_payloads import assemble_local_turn_payload
from vantage_v5.services.turn_payloads import assemble_scenario_lab_fallback_payload
from vantage_v5.services.turn_payloads import assemble_service_turn_payload
from vantage_v5.services.turn_payloads import build_local_turn_parts
from vantage_v5.services.turn_payloads import LocalTurnBodyParts
from vantage_v5.services.turn_payloads import LocalTurnContext
from vantage_v5.services.turn_payloads import ScenarioLabFallbackParts
from vantage_v5.services.turn_payloads import ServiceTurnPayloadParts
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
        attention_selection = None
        selected_attention_resources = ()
        if attention_turn is not None:
            attention_selection, selected_attention_resources = attention_turn.select(
                navigation.attention_selection,
            )
        selected_attention_payload = [resource.to_dict() for resource in selected_attention_resources]
        model_visible_artifacts = context.visible_artifacts
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
        suppress_auto_graph_writes = False
        if _is_open_only_whiteboard_invocation(surface_invocation_payload):
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
        attention_state_payload = attention_payload(
            turn=attention_turn,
            selection=attention_selection,
            selected_resources=selected_attention_resources,
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
        turn_stage = build_turn_stage(
            navigation_mode=navigation.mode,
            whiteboard_mode=resolved_whiteboard_mode if navigation.mode == "chat" else "chat",
            public_summary=navigation.reason,
        )
        close_surface_action = _surface_close_action(surface_invocation_payload)
        if close_surface_action is not None:
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
                        assistant_message=_close_surface_assistant_message(close_surface_action),
                        mode="local_action",
                    ),
                    turn_interpretation=turn_interpretation_parts,
                    turn_stage=turn_stage,
                )
            )
            payload.update(attention_state_payload)
            return payload
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
            payload.update(attention_state_payload)
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
                memory_intent=request.memory_intent,
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
                suppress_auto_graph_writes=suppress_auto_graph_writes,
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
        payload.update(attention_state_payload)
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
            suppress_auto_graph_writes=_is_open_only_whiteboard_invocation(surface_invocation),
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
            payload.update(attention_state_payload)
        trace_path = getattr(turn, "trace_path", None)
        if trace_path:
            payload["_turn_trace_path"] = trace_path
        return payload


def _is_open_only_whiteboard_invocation(surface_invocation: dict[str, Any]) -> bool:
    if str(surface_invocation.get("write_behavior") or "").strip().lower() != "open_only":
        return False
    primary = str(surface_invocation.get("primary_surface") or "").strip().lower()
    if primary == "whiteboard":
        return True
    for surface in surface_invocation.get("surfaces") or []:
        if not isinstance(surface, dict):
            continue
        if str(surface.get("kind") or "").strip().lower() == "whiteboard":
            return True
    return False


def _surface_close_action(surface_invocation: dict[str, Any]) -> dict[str, Any] | None:
    action = surface_invocation.get("surface_action") if isinstance(surface_invocation, dict) else None
    if not isinstance(action, dict):
        return None
    if str(action.get("type") or "").strip() != "close_visible_surface":
        return None
    return action


def _close_surface_assistant_message(action: dict[str, Any]) -> str:
    if action.get("status") == "no_visible_surface":
        return "I don't see a visible surface to close."
    title = str(action.get("title") or "").strip()
    target = str(action.get("target") or action.get("target_kind") or "surface").strip().replace("_", " ")
    if title:
        return f"Closed {title} from view."
    return f"Closed the {target} from view."


def _safe_scenario_lab_error_message(error: Exception) -> str:
    raw = str(error)
    if "rate limit" in raw.lower() or "openai" in type(error).__module__.lower():
        return "Scenario Lab could not complete because the model provider was temporarily unavailable. The turn stayed in chat so you can retry or continue from here."
    return "Scenario Lab could not complete this turn. The turn stayed in chat so you can retry or continue from here."
