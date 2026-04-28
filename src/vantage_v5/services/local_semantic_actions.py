from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactLifecycle
from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactRuntime
from vantage_v5.services.record_cards import serialize_saved_note_card
from vantage_v5.services.semantic_frame import SemanticFrame
from vantage_v5.services.semantic_policy import SemanticPolicyContext
from vantage_v5.services.turn_payloads import build_local_turn_parts
from vantage_v5.services.turn_payloads import LocalTurnBodyParts
from vantage_v5.services.turn_payloads import LocalTurnContext
from vantage_v5.services.turn_payloads import TurnResultParts
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(frozen=True, slots=True)
class LocalSemanticTurnContext:
    runtime: dict[str, Any]
    session: Any
    message: str
    history: list[dict[str, str]]
    workspace: WorkspaceDocument
    workspace_scope: str
    transient_workspace: bool
    semantic_frame: dict[str, Any]
    semantic_policy: dict[str, Any]
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None


class LocalSemanticActionEngine:
    """Owns deterministic local actions chosen by semantic policy."""

    def __init__(self, *, draft_artifact_lifecycle: DraftArtifactLifecycle) -> None:
        self.draft_artifact_lifecycle = draft_artifact_lifecycle

    def policy_context(
        self,
        *,
        semantic_frame: SemanticFrame,
        session: Any,
        workspace: WorkspaceDocument,
        workspace_scope: str,
        pinned_context: dict[str, Any] | None,
        pending_workspace_update: dict[str, Any] | None,
        user_message: str,
    ) -> SemanticPolicyContext:
        workspace_in_scope = workspace_scope != "excluded" and bool(workspace.content.strip())
        publish_target_confirmed = workspace_in_scope and _is_current_workspace_artifact_request(user_message)
        return SemanticPolicyContext(
            has_current_artifact=workspace_in_scope,
            has_pending_whiteboard=bool(pending_workspace_update),
            has_pinned_context=bool(pinned_context),
            has_active_experiment=session is not None,
            has_inspectable_context=bool(pinned_context or workspace_in_scope),
            publish_target_confirmed=publish_target_confirmed
            or semantic_frame.referenced_object is not None and workspace_in_scope,
        )

    def build_turn_parts(self, context: LocalSemanticTurnContext) -> TurnResultParts | None:
        local_context = self._local_turn_context(context)
        action_type = str(
            context.semantic_policy.get("action_type")
            or context.semantic_policy.get("semantic_action")
            or ""
        ).strip()
        should_clarify = bool(
            context.semantic_policy.get("should_clarify")
            or context.semantic_policy.get("needs_clarification")
        )
        if should_clarify:
            return build_local_turn_parts(
                local_context,
                turn_body=LocalTurnBodyParts(
                    assistant_message=str(
                        context.semantic_policy.get("clarification_prompt")
                        or "Can you clarify what you want me to do?"
                    ),
                    mode="clarification",
                ),
            )
        if action_type == "artifact_save":
            return self._save_current_whiteboard(context, local_context=local_context)
        if action_type == "artifact_publish":
            return self._publish_current_whiteboard(context, local_context=local_context)
        if action_type == "experiment_manage":
            return self._experiment_status(context, local_context=local_context)
        return None

    def session_info(self, session: Any) -> dict[str, Any]:
        if session is None:
            return {"active": False, "session_id": None, "saved_note_count": 0}
        return {
            "active": True,
            "session_id": session.session_id,
            "saved_note_count": (
                len(MemoryStore(session.memories_dir).list_memories())
                + len(ArtifactStore(session.artifacts_dir).list_artifacts())
            ),
        }

    def _save_current_whiteboard(
        self,
        context: LocalSemanticTurnContext,
        *,
        local_context: LocalTurnContext,
    ) -> TurnResultParts:
        result = self.draft_artifact_lifecycle.save_visible_whiteboard_snapshot(
            runtime=DraftArtifactRuntime.from_mapping(context.runtime),
            workspace=context.workspace,
        )
        created_record = serialize_saved_note_card(result.artifact, scope=result.scope) if result.artifact else None
        return build_local_turn_parts(
            local_context,
            turn_body=LocalTurnBodyParts(
                assistant_message=result.assistant_message or "I saved the whiteboard as a snapshot.",
                mode="local_action",
                graph_action=result.graph_action,
                created_record=created_record,
            ),
            workspace=result.workspace,
            transient_workspace=True,
        )

    def _publish_current_whiteboard(
        self,
        context: LocalSemanticTurnContext,
        *,
        local_context: LocalTurnContext,
    ) -> TurnResultParts:
        result = self.draft_artifact_lifecycle.publish_visible_whiteboard(
            runtime=DraftArtifactRuntime.from_mapping(context.runtime),
            workspace=context.workspace,
        )
        created_record = serialize_saved_note_card(result.artifact, scope=result.scope) if result.artifact else None
        return build_local_turn_parts(
            local_context,
            turn_body=LocalTurnBodyParts(
                assistant_message=result.assistant_message or "I published the whiteboard as a reusable artifact.",
                mode="local_action",
                graph_action=result.graph_action,
                created_record=created_record,
            ),
            workspace=result.workspace,
            transient_workspace=True,
        )

    def _experiment_status(
        self,
        context: LocalSemanticTurnContext,
        *,
        local_context: LocalTurnContext,
    ) -> TurnResultParts:
        normalized_message = _normalize_message(context.message).lower()
        if context.session is None:
            assistant_message = "You're in durable mode. There isn't an active experiment to end."
        elif re.search(r"\b(?:end|exit|leave|turn off|stop|switch out)\b", normalized_message):
            assistant_message = (
                "Experiment mode is active. I can end it after you confirm; ending it discards temporary notes from this session."
            )
        else:
            assistant_message = "Experiment mode is active, so temporary notes stay in this session."
        return build_local_turn_parts(
            local_context,
            turn_body=LocalTurnBodyParts(
                assistant_message=assistant_message,
                mode="local_action",
            ),
        )

    def _local_turn_context(self, context: LocalSemanticTurnContext) -> LocalTurnContext:
        return LocalTurnContext(
            user_message=context.message,
            history=context.history,
            workspace=context.workspace,
            workspace_scope=context.workspace_scope,
            runtime_scope=context.runtime["scope"],
            transient_workspace=context.transient_workspace,
            semantic_frame=context.semantic_frame,
            semantic_policy=context.semantic_policy,
            pinned_context_id=context.pinned_context_id,
            pinned_context=context.pinned_context,
            experiment=self.session_info(context.session),
        )


def _normalize_message(message: str | None) -> str:
    return str(message or "").strip()


def _is_current_workspace_artifact_request(message: str | None) -> bool:
    normalized = _normalize_message(message).lower()
    if not normalized:
        return False
    return bool(
        re.search(r"\b(?:this|current|whiteboard|draft|work product|artifact)\b", normalized)
        or re.search(r"\b(?:save|publish)\s+(?:it|this)\b", normalized)
    )
