from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vantage_v5.services.context_support import ContextSupport
from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass
class _WorkspaceStore:
    workspaces_dir: Path


def _support() -> ContextSupport:
    return ContextSupport(whiteboard_routing=WhiteboardRoutingEngine())


def _document(tmp_path: Path, content: str, metadata: dict[str, str] | None = None) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id="active-workspace",
        title="Active Workspace",
        content=content,
        path=tmp_path / "active-workspace.md",
        scenario_metadata=metadata,
    )


def test_normalize_workspace_scope_uses_live_buffer_and_explicit_whiteboard_request() -> None:
    support = _support()

    assert support.normalize_workspace_scope("PINNED", workspace_content=None, user_message="hello") == "pinned"
    assert support.normalize_workspace_scope(None, workspace_content="# Draft", user_message="hello") == "visible"
    assert (
        support.normalize_workspace_scope(None, workspace_content=None, user_message="Please draft that in the whiteboard")
        == "requested"
    )
    assert support.normalize_workspace_scope(None, workspace_content=None, user_message="hello") == "excluded"


def test_workspace_helpers_preserve_hidden_whiteboard_safety_and_unsaved_metadata(tmp_path: Path) -> None:
    support = _support()
    store = _WorkspaceStore(workspaces_dir=tmp_path)
    content = "\n".join(
        [
            "# Branch Draft",
            "",
            "## Scenario Metadata",
            "- scenario_kind: branch",
            "- base_workspace_id: base",
            "- branch_label: Budget",
        ]
    )

    unsaved = support.workspace_from_unsaved_buffer(store, "branch-workspace--budget", content)
    redacted = support.workspace_without_context(unsaved)

    assert unsaved.title == "Branch Draft"
    assert unsaved.path == tmp_path / "branch-workspace--budget.md"
    assert unsaved.scenario_metadata == {
        "scenario_kind": "branch",
        "base_workspace_id": "base",
        "branch_label": "Budget",
        "scenario_namespace_id": "branch-workspace",
        "namespace_mode": "detached",
    }
    assert redacted.content == ""
    assert redacted.scenario_metadata == unsaved.scenario_metadata


def test_workspace_from_buffer_preserves_existing_scenario_metadata_when_buffer_has_none(tmp_path: Path) -> None:
    support = _support()
    document = _document(tmp_path, "# Saved Branch", metadata={"scenario_kind": "branch", "branch_label": "A"})

    buffered = support.workspace_from_buffer(document, "# Edited Title\n\nNo metadata block in browser buffer.")

    assert buffered.title == "Edited Title"
    assert buffered.content == "# Edited Title\n\nNo metadata block in browser buffer."
    assert buffered.scenario_metadata == {"scenario_kind": "branch", "branch_label": "A"}


def test_pending_workspace_update_normalization_and_carry_rules_are_narrow() -> None:
    support = _support()
    pending = support.normalize_pending_workspace_update(
        {
            "type": "offer_whiteboard",
            "summary": "Draft the email in the whiteboard.",
            "origin_user_message": "Draft an email to Jay.",
        }
    )

    assert pending == {
        "type": "offer_whiteboard",
        "status": "offered",
        "summary": "Draft the email in the whiteboard.",
        "origin_user_message": "Draft an email to Jay.",
        "origin_assistant_message": None,
    }
    assert support.should_carry_pending_workspace_update("yes, let's do that", pending) is True
    assert support.should_carry_pending_workspace_update("which one?", pending) is True
    assert support.should_carry_pending_workspace_update("Start a fresh plan in the whiteboard", pending) is False
    assert support.should_carry_pending_workspace_update("continue", pending) is False
    assert support.should_carry_pending_workspace_update("x" * 241, pending) is False


def test_pending_workspace_update_requires_origin_for_carry() -> None:
    support = _support()
    pending = support.normalize_pending_workspace_update({"status": "draft_ready", "summary": "Missing origin."})

    assert pending is not None
    assert pending["type"] == "draft_whiteboard"
    assert support.should_carry_pending_workspace_update("yes", pending) is False


def test_whiteboard_entry_mode_distinguishes_hidden_existing_and_fresh_starts() -> None:
    support = _support()

    assert (
        support.whiteboard_entry_mode(
            workspace_loaded=True,
            workspace_content="# Hidden",
            workspace_scope="excluded",
            source_summary={"source_record_id": "memory-1"},
        )
        is None
    )
    assert (
        support.whiteboard_entry_mode(
            workspace_loaded=True,
            workspace_content=None,
            workspace_scope="visible",
            source_summary={"source_record_id": "memory-1"},
        )
        == "started_from_prior_material"
    )
    assert (
        support.whiteboard_entry_mode(
            workspace_loaded=True,
            workspace_content="# Current draft",
            workspace_scope="visible",
            source_summary=None,
        )
        == "continued_current"
    )
    assert (
        support.whiteboard_entry_mode(
            workspace_loaded=False,
            workspace_content="# New draft",
            workspace_scope="visible",
            source_summary=None,
        )
        == "started_fresh"
    )
