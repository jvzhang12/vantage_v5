from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from vantage_v5.services.context_support import ContextSupport
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(slots=True)
class ChatTurnRequestContext:
    durable_scope: dict[str, Any]
    message: str
    history: list[dict[str, str]]
    workspace_id: str | None
    workspace_scope: str
    workspace_content: str | None
    whiteboard_mode: str
    pinned_context_id: str | None
    memory_intent: str
    pending_workspace_update: dict[str, Any] | None
    navigation: Any | None = None
    force_pending_workspace_update: bool = False


@dataclass(slots=True)
class PreparedTurnContext:
    session: Any
    runtime: dict[str, Any]
    resolved_workspace_id: str
    normalized_workspace_scope: str
    workspace_loaded: bool
    workspace: WorkspaceDocument
    transient_workspace: bool
    pinned_context: dict[str, Any] | None
    pending_workspace_update: dict[str, Any] | None
    whiteboard_entry_mode: str | None
    continuity_context: dict[str, Any]


@dataclass(slots=True)
class ContextEngineHooks:
    runtime_for: Callable[..., dict[str, Any]]
    pinned_context_summary: Callable[..., dict[str, Any] | None]
    whiteboard_source_summary: Callable[..., dict[str, Any] | None]
    navigator_continuity_context: Callable[..., dict[str, Any]]


class ContextEngine:
    def __init__(
        self,
        *,
        hooks: ContextEngineHooks,
        context_support: ContextSupport,
        default_workspace_id: str,
    ) -> None:
        self.hooks = hooks
        self.context_support = context_support
        self.default_workspace_id = default_workspace_id

    def prepare_turn_context(self, request: ChatTurnRequestContext) -> PreparedTurnContext:
        experiment_manager = request.durable_scope["experiment_manager"]
        session = experiment_manager.get_active_session()
        runtime = self.hooks.runtime_for(request.durable_scope, session)
        resolved_workspace_id = (
            request.workspace_id
            or runtime["state_store"].get_active_workspace_id(default_workspace_id=self.default_workspace_id)
        )
        normalized_workspace_scope = self.context_support.normalize_workspace_scope(
            request.workspace_scope,
            workspace_content=request.workspace_content,
            user_message=request.message,
        )
        workspace_loaded = True
        try:
            workspace = runtime["workspace_store"].load(resolved_workspace_id)
        except FileNotFoundError:
            workspace_loaded = False
            if normalized_workspace_scope == "excluded":
                workspace = self.context_support.workspace_from_unsaved_buffer(
                    runtime["workspace_store"],
                    resolved_workspace_id,
                    "",
                )
            elif request.workspace_content is None:
                raise
            else:
                workspace = self.context_support.workspace_from_unsaved_buffer(
                    runtime["workspace_store"],
                    resolved_workspace_id,
                    request.workspace_content,
                )

        transient_workspace = normalized_workspace_scope != "excluded" and request.workspace_content is not None
        if normalized_workspace_scope == "excluded":
            workspace = self.context_support.workspace_without_context(workspace)
        elif request.workspace_content is not None:
            workspace = self.context_support.workspace_from_buffer(workspace, request.workspace_content)

        pinned_context = self.hooks.pinned_context_summary(
            request.durable_scope,
            session,
            runtime,
            request.pinned_context_id,
        )
        pending_workspace_update = self.context_support.normalize_pending_workspace_update(request.pending_workspace_update)
        if (
            not request.force_pending_workspace_update
            and not self.context_support.should_carry_pending_workspace_update(request.message, pending_workspace_update)
        ):
            pending_workspace_update = None

        whiteboard_entry_mode = self.context_support.whiteboard_entry_mode(
            workspace_loaded=workspace_loaded,
            workspace_content=request.workspace_content,
            workspace_scope=normalized_workspace_scope,
            source_summary=self.hooks.whiteboard_source_summary(
                request.durable_scope,
                session,
                runtime,
                resolved_workspace_id,
            )
            if workspace_loaded
            else None,
        )
        continuity_context = self.hooks.navigator_continuity_context(
            request.durable_scope,
            session,
            runtime,
            workspace=workspace,
            workspace_scope=normalized_workspace_scope,
        )
        return PreparedTurnContext(
            session=session,
            runtime=runtime,
            resolved_workspace_id=resolved_workspace_id,
            normalized_workspace_scope=normalized_workspace_scope,
            workspace_loaded=workspace_loaded,
            workspace=workspace,
            transient_workspace=transient_workspace,
            pinned_context=pinned_context,
            pending_workspace_update=pending_workspace_update,
            whiteboard_entry_mode=whiteboard_entry_mode,
            continuity_context=continuity_context,
        )
