from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import ContextEngine
from vantage_v5.services.context_engine import ContextEngineHooks
from vantage_v5.services.context_support import ContextSupport
from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass
class _ExperimentManager:
    session: object | None = None

    def get_active_session(self) -> object | None:
        return self.session


@dataclass
class _StateStore:
    active_workspace_id: str

    def get_active_workspace_id(self, *, default_workspace_id: str) -> str:
        return self.active_workspace_id or default_workspace_id


class _WorkspaceStore:
    def __init__(self, root: Path, documents: dict[str, WorkspaceDocument] | None = None) -> None:
        self.workspaces_dir = root
        self.documents = documents or {}

    def load(self, workspace_id: str) -> WorkspaceDocument:
        try:
            return self.documents[workspace_id]
        except KeyError:
            raise FileNotFoundError(workspace_id) from None


def _document(tmp_path: Path, workspace_id: str, content: str) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id=workspace_id,
        title=workspace_id.replace("-", " ").title(),
        content=content,
        path=tmp_path / f"{workspace_id}.md",
        scenario_metadata=None,
    )


def _engine(
    tmp_path: Path,
    *,
    workspace_store: _WorkspaceStore,
) -> ContextEngine:
    runtime = {
        "state_store": _StateStore("active-workspace"),
        "workspace_store": workspace_store,
        "scope": "durable",
    }

    return ContextEngine(
        default_workspace_id="default-workspace",
        context_support=ContextSupport(whiteboard_routing=WhiteboardRoutingEngine()),
        hooks=ContextEngineHooks(
            runtime_for=lambda durable_scope, session: runtime,
            pinned_context_summary=lambda durable_scope, session, runtime, record_id: (
                {"id": record_id, "title": "Pinned record"} if record_id else None
            ),
            whiteboard_source_summary=lambda durable_scope, session, runtime, workspace_id: None,
            navigator_continuity_context=lambda durable_scope, session, runtime, *, workspace, workspace_scope: {
                "current_whiteboard": {
                    "workspace_id": workspace.workspace_id,
                    "scope": workspace_scope,
                    "content_excerpt": workspace.content[:120],
                }
            },
        ),
    )


def _request(**overrides: Any) -> ChatTurnRequestContext:
    defaults: dict[str, Any] = {
        "durable_scope": {"experiment_manager": _ExperimentManager()},
        "message": "What should we do next?",
        "history": [],
        "workspace_id": "active-workspace",
        "workspace_scope": "excluded",
        "workspace_content": None,
        "whiteboard_mode": "auto",
        "pinned_context_id": None,
        "memory_intent": "auto",
        "pending_workspace_update": None,
    }
    defaults.update(overrides)
    return ChatTurnRequestContext(**defaults)


def test_prepare_turn_context_redacts_hidden_workspace_content(tmp_path: Path) -> None:
    store = _WorkspaceStore(
        tmp_path,
        {"active-workspace": _document(tmp_path, "active-workspace", "persisted hidden draft body")},
    )
    context = _engine(tmp_path, workspace_store=store).prepare_turn_context(
        _request(
            workspace_scope="excluded",
            workspace_content="unsaved hidden draft body",
        )
    )

    assert context.normalized_workspace_scope == "excluded"
    assert context.workspace_loaded is True
    assert context.workspace.content == ""
    assert context.transient_workspace is False
    assert context.whiteboard_entry_mode is None
    assert context.continuity_context["current_whiteboard"]["content_excerpt"] == ""


def test_prepare_turn_context_excluded_missing_workspace_uses_empty_buffer(tmp_path: Path) -> None:
    store = _WorkspaceStore(tmp_path)
    context = _engine(tmp_path, workspace_store=store).prepare_turn_context(
        _request(
            workspace_id="missing-workspace",
            workspace_scope="excluded",
            workspace_content="hidden unsaved body",
        )
    )

    assert context.resolved_workspace_id == "missing-workspace"
    assert context.workspace_loaded is False
    assert context.workspace.workspace_id == "missing-workspace"
    assert context.workspace.content == ""
    assert context.continuity_context["current_whiteboard"]["content_excerpt"] == ""


def test_prepare_turn_context_carries_active_pending_whiteboard_update(tmp_path: Path) -> None:
    pending = {
        "type": "offer_whiteboard",
        "summary": "Draft the email in the whiteboard.",
        "origin_user_message": "Draft an email to Judy.",
    }
    store = _WorkspaceStore(
        tmp_path,
        {"active-workspace": _document(tmp_path, "active-workspace", "current draft")},
    )
    context = _engine(
        tmp_path,
        workspace_store=store,
    ).prepare_turn_context(
        _request(
            message="yes, let's do that",
            workspace_scope="visible",
            pending_workspace_update=pending,
        )
    )

    assert context.pending_workspace_update is not None
    assert context.pending_workspace_update["type"] == "offer_whiteboard"
    assert context.pending_workspace_update["status"] == "offered"


def test_prepare_turn_context_drops_stale_pending_whiteboard_update(tmp_path: Path) -> None:
    pending = {
        "type": "offer_whiteboard",
        "status": "offered",
        "summary": "Draft the old email in the whiteboard.",
        "origin_user_message": "Draft an email to Judy.",
    }
    store = _WorkspaceStore(
        tmp_path,
        {"active-workspace": _document(tmp_path, "active-workspace", "current draft")},
    )
    context = _engine(tmp_path, workspace_store=store).prepare_turn_context(
        _request(
            message="Start a new road trip plan in the whiteboard.",
            workspace_scope="visible",
            pending_workspace_update=pending,
        )
    )

    assert context.pending_workspace_update is None


def test_prepare_turn_context_force_keeps_pending_whiteboard_update(tmp_path: Path) -> None:
    pending = {
        "type": "offer_whiteboard",
        "status": "offered",
        "summary": "Draft the old email in the whiteboard.",
        "origin_user_message": "Draft an email to Judy.",
    }
    store = _WorkspaceStore(
        tmp_path,
        {"active-workspace": _document(tmp_path, "active-workspace", "current draft")},
    )
    context = _engine(tmp_path, workspace_store=store).prepare_turn_context(
        _request(
            message="Start a new road trip plan in the whiteboard.",
            workspace_scope="visible",
            pending_workspace_update=pending,
            force_pending_workspace_update=True,
        )
    )

    assert context.pending_workspace_update == {
        **pending,
        "origin_assistant_message": None,
    }
