from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


WHITEBOARD_TYPE_TO_STATUS = {
    "offer_whiteboard": "offered",
    "draft_whiteboard": "draft_ready",
}
WHITEBOARD_STATUS_TO_TYPE = {status: kind for kind, status in WHITEBOARD_TYPE_TO_STATUS.items()}


@dataclass(frozen=True, slots=True)
class ContextSupport:
    """Pure context-preparation helpers that do not need app runtime state."""

    whiteboard_routing: WhiteboardRoutingEngine

    def normalize_workspace_scope(
        self,
        value: str | None,
        *,
        workspace_content: str | None,
        user_message: str | None,
    ) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"excluded", "visible", "pinned", "requested"}:
            return normalized
        if workspace_content is not None:
            return "visible"
        if self.whiteboard_routing.is_explicit_whiteboard_draft_request(user_message):
            return "requested"
        return "excluded"

    def workspace_from_buffer(self, document: WorkspaceDocument, content: str) -> WorkspaceDocument:
        scenario_metadata = WorkspaceStore.parse_scenario_metadata(content, workspace_id=document.workspace_id)
        return WorkspaceDocument(
            workspace_id=document.workspace_id,
            title=WorkspaceStore._title_from_content(document.workspace_id, content),
            content=content,
            path=document.path,
            scenario_metadata=scenario_metadata or document.scenario_metadata,
        )

    def workspace_from_unsaved_buffer(
        self,
        workspace_store: WorkspaceStore,
        workspace_id: str,
        content: str,
    ) -> WorkspaceDocument:
        path = workspace_store.workspaces_dir / f"{workspace_id}.md"
        return WorkspaceDocument(
            workspace_id=workspace_id,
            title=WorkspaceStore._title_from_content(workspace_id, content),
            content=content,
            path=path,
            scenario_metadata=WorkspaceStore.parse_scenario_metadata(content, workspace_id=workspace_id),
        )

    def workspace_without_context(self, document: WorkspaceDocument) -> WorkspaceDocument:
        return WorkspaceDocument(
            workspace_id=document.workspace_id,
            title=document.title,
            content="",
            path=document.path,
            scenario_metadata=document.scenario_metadata,
        )

    def normalize_pending_workspace_update(self, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        workspace_type = str(value.get("type") or "").strip() or None
        workspace_status = str(value.get("status") or "").strip() or None
        if workspace_status is None and workspace_type is not None:
            workspace_status = WHITEBOARD_TYPE_TO_STATUS.get(workspace_type)
        if workspace_type is None and workspace_status is not None:
            workspace_type = WHITEBOARD_STATUS_TO_TYPE.get(workspace_status)
        normalized = {
            "type": workspace_type,
            "status": workspace_status,
            "summary": str(value.get("summary") or "").strip() or None,
            "origin_user_message": str(value.get("origin_user_message") or "").strip() or None,
            "origin_assistant_message": str(value.get("origin_assistant_message") or "").strip() or None,
        }
        if not any(normalized.values()):
            return None
        return normalized

    def should_carry_pending_workspace_update(
        self,
        message: str | None,
        pending_workspace_update: dict[str, Any] | None,
    ) -> bool:
        return self.whiteboard_routing.should_carry_pending_workspace_update(
            message,
            pending_workspace_update,
        )

    def whiteboard_entry_mode(
        self,
        *,
        workspace_loaded: bool,
        workspace_content: str | None,
        workspace_scope: str,
        source_summary: dict[str, Any] | None,
    ) -> str | None:
        if workspace_scope == "excluded":
            return None
        if workspace_loaded and source_summary is not None:
            return "started_from_prior_material"
        if workspace_content is None:
            return None
        return "continued_current" if workspace_loaded else "started_fresh"
