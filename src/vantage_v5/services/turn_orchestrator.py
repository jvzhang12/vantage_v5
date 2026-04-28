from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import logging
from typing import Any, Callable

from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import ContextEngine
from vantage_v5.services.local_semantic_actions import LocalSemanticActionEngine
from vantage_v5.services.local_semantic_actions import LocalSemanticTurnContext
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.protocol_engine import ProtocolEngine
from vantage_v5.services.semantic_frame import build_semantic_frame
from vantage_v5.services.semantic_policy import decide_semantic_policy
from vantage_v5.services.turn_payloads import assemble_local_turn_payload
from vantage_v5.services.turn_payloads import assemble_scenario_lab_fallback_payload
from vantage_v5.services.turn_payloads import assemble_service_turn_payload
from vantage_v5.services.turn_payloads import ScenarioLabFallbackParts
from vantage_v5.services.turn_payloads import ServiceTurnPayloadParts
from vantage_v5.services.turn_payloads import TurnInterpretationParts
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
    ) -> None:
        self.navigator_service = navigator_service
        self.context_engine = context_engine
        self.protocol_engine = protocol_engine
        self.local_semantic_actions = local_semantic_actions
        self.whiteboard_routing = whiteboard_routing
        self.hooks = hooks

    def run(self, request: ChatTurnRequestContext) -> dict[str, Any]:
        context = self.context_engine.prepare_turn_context(request)
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
            )
        resolved_whiteboard_mode = self.whiteboard_routing.resolve_whiteboard_mode(
            request.whiteboard_mode,
            navigation,
            user_message=request.message,
            workspace=context.workspace,
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
        )
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
            return assemble_local_turn_payload(
                replace(local_semantic_parts, turn_interpretation=turn_interpretation_parts)
            )

        if self.hooks.should_enter_scenario_lab(navigation):
            try:
                turn = context.runtime["scenario_lab_service"].run(
                    message=request.message,
                    workspace=context.workspace,
                    history=request.history,
                    navigation=navigation,
                    selected_record_id=request.pinned_context_id,
                    pending_workspace_update=context.pending_workspace_update,
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
                    error=exc,
                )
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
                applied_protocol_kinds=applied_protocol_kinds,
            )

        return assemble_service_turn_payload(
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
            )
        )

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
        error: Exception,
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
            applied_protocol_kinds=applied_protocol_kinds,
        )
        return assemble_scenario_lab_fallback_payload(
            ScenarioLabFallbackParts(
                turn_body=turn.to_body_parts(),
                navigation=navigation.to_dict(),
                comparison_question=navigation.comparison_question,
                reason=navigation.reason,
                error_type=type(error).__name__,
                error_message=str(error),
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
            )
        )
