from __future__ import annotations

from pathlib import Path

import pytest

from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactLifecycle
from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactRuntime
from vantage_v5.services.draft_artifact_lifecycle import artifact_lifecycle_card_fields
from vantage_v5.services.draft_artifact_lifecycle import artifact_lifecycle_kind
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


def _runtime(
    tmp_path: Path,
    *,
    scope: str = "durable",
    reference_concept_store: ConceptStore | None = None,
    reference_memory_store: MemoryStore | None = None,
    reference_artifact_store: ArtifactStore | None = None,
) -> DraftArtifactRuntime:
    concept_store = ConceptStore(tmp_path / "concepts")
    memory_store = MemoryStore(tmp_path / "memories")
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    workspace_store = WorkspaceStore(tmp_path / "workspaces")
    state_store = ActiveWorkspaceStateStore(tmp_path / "state" / "active_workspace.json")
    executor = GraphActionExecutor(
        concept_store=concept_store,
        memory_store=memory_store,
        artifact_store=artifact_store,
        workspace_store=workspace_store,
        state_store=state_store,
        reference_concept_store=reference_concept_store,
        reference_memory_store=reference_memory_store,
        reference_artifact_store=reference_artifact_store,
    )
    return DraftArtifactRuntime(
        workspace_store=workspace_store,
        artifact_store=artifact_store,
        state_store=state_store,
        executor=executor,
        scope=scope,
    )


def _workspace(tmp_path: Path, workspace_id: str, content: str) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id=workspace_id,
        title=WorkspaceStore._title_from_content(workspace_id, content),
        content=content,
        path=tmp_path / "workspaces" / f"{workspace_id}.md",
        scenario_metadata=None,
    )


def test_save_visible_whiteboard_snapshot_persists_workspace_and_snapshot(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()
    workspace = _workspace(tmp_path, "launch-notes", "# Launch Notes\n\nShip carefully.")

    result = lifecycle.save_visible_whiteboard_snapshot(runtime=runtime, workspace=workspace)

    assert result.workspace.workspace_id == "launch-notes"
    assert result.workspace.path.exists()
    assert runtime.state_store.get_active_workspace_id(default_workspace_id="fallback") == "launch-notes"
    assert result.action.action == "save_workspace_iteration_artifact"
    assert result.artifact is not None
    assert result.artifact.comes_from == ["launch-notes"]
    assert artifact_lifecycle_card_fields(result.artifact) == {
        "artifact_origin": "whiteboard",
        "artifact_lifecycle": "whiteboard_snapshot",
    }
    assert artifact_lifecycle_kind(result.artifact) == "whiteboard_snapshot"
    assert result.assistant_message == "I saved Launch Notes as a whiteboard snapshot."


def test_save_workspace_update_returns_snapshot_result(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()

    result = lifecycle.save_workspace_update(
        runtime=runtime,
        workspace_id="daily-plan",
        content="# Daily Plan\n\nFocus work first.",
    )

    assert result.workspace.title == "Daily Plan"
    assert result.graph_action["type"] == "save_workspace_iteration_artifact"
    assert result.artifact is not None
    assert result.artifact.title == "Daily Plan"
    assert runtime.state_store.get_active_workspace_id(default_workspace_id="fallback") == "daily-plan"


def test_publish_visible_whiteboard_promotes_without_saving_workspace(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()
    workspace = _workspace(tmp_path, "unsaved-brief", "# Unsaved Brief\n\nPublishable content.")

    result = lifecycle.publish_visible_whiteboard(runtime=runtime, workspace=workspace)

    assert result.workspace.workspace_id == "unsaved-brief"
    assert not result.workspace.path.exists()
    assert result.action.action == "promote_workspace_to_artifact"
    assert result.artifact is not None
    assert result.artifact.title == "Unsaved Brief"
    assert artifact_lifecycle_kind(result.artifact) == "promoted_artifact"


def test_promote_whiteboard_to_artifact_uses_unsaved_buffer_without_persisting_workspace(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()

    result = lifecycle.promote_whiteboard_to_artifact(
        runtime=runtime,
        workspace_id="email-draft",
        content="# Email Draft\n\nHi Sam, checking in.",
        title="Email Draft To Sam",
    )

    assert result.workspace.workspace_id == "email-draft"
    assert result.workspace.title == "Email Draft"
    assert not result.workspace.path.exists()
    assert result.artifact is not None
    assert result.artifact.title == "Email Draft To Sam"
    assert result.artifact.comes_from == ["email-draft"]
    assert artifact_lifecycle_card_fields(result.artifact) == {
        "artifact_origin": "whiteboard",
        "artifact_lifecycle": "promoted_artifact",
    }


def test_open_saved_item_into_whiteboard_supports_saved_record_types(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()
    records = [
        runtime.executor.concept_store.create_concept(
            title="Reopen Concept",
            card="A concept card.",
            body="Concept body.",
        ),
        runtime.executor.memory_store.create_memory(
            title="Reopen Memory",
            card="A memory card.",
            body="Memory body.",
        ),
        runtime.executor.artifact_store.create_artifact(
            title="Reopen Artifact",
            card="An artifact card.",
            body="Artifact body.",
        ),
    ]

    for record in records:
        result = lifecycle.open_saved_item_into_whiteboard(runtime=runtime, record_id=record.id)

        assert result.workspace.workspace_id == record.id
        assert result.workspace.path.exists()
        assert result.workspace.content == f"# {record.title}\n\n> {record.card}\n\n{record.body}\n"
        assert result.action.action == "open_saved_item_into_workspace"
        assert result.action.record_id == record.id
        assert result.action.source == record.source
        assert result.artifact is None
        assert result.scope == "durable"
        assert runtime.state_store.get_active_workspace_id(default_workspace_id="fallback") == record.id


def test_open_saved_item_into_whiteboard_rejects_protocol_records(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()
    protocol = runtime.executor.concept_store.upsert_protocol(
        protocol_id="email-drafting-protocol",
        title="Email Drafting Protocol",
        card="Reusable email drafting guidance.",
        body="Use this for drafting emails.",
        protocol_kind="email",
        variables={},
        applies_to=["email"],
    )

    with pytest.raises(ValueError, match="Protocols are guidance objects"):
        lifecycle.open_saved_item_into_whiteboard(runtime=runtime, record_id=protocol.id)


def test_artifact_lifecycle_card_fields_only_enriches_artifacts(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    concept = runtime.executor.concept_store.create_concept(
        title="Plain Concept",
        card="Not an artifact.",
        body="No lifecycle card fields should be added.",
    )
    artifact = runtime.executor.artifact_store.create_artifact(
        title="Comparison Hub",
        card="Scenario comparison artifact.",
        body="# Comparison Hub\n\n## Branches Compared\n- branch-a\n- branch-b\n\n## Recommendation\nChoose branch A.",
        type="scenario_comparison",
        comes_from=["base-workspace", "branch-a", "branch-b"],
    )

    assert artifact_lifecycle_card_fields(concept) == {}
    assert artifact_lifecycle_card_fields(artifact) == {
        "artifact_origin": "scenario_lab",
        "artifact_lifecycle": "comparison_hub",
    }
    assert artifact_lifecycle_kind(concept) == ""
    assert artifact_lifecycle_kind(artifact) == "comparison_hub"


def test_open_saved_item_into_whiteboard_uses_experiment_workspace_for_reference_records(tmp_path: Path) -> None:
    durable_memory_store = MemoryStore(tmp_path / "durable" / "memories")
    record = durable_memory_store.create_memory(
        title="Durable Preference",
        card="Reference memory card.",
        body="Reference memory body.",
    )
    runtime = _runtime(
        tmp_path / "experiment",
        scope="experiment",
        reference_memory_store=durable_memory_store,
    )
    lifecycle = DraftArtifactLifecycle()

    result = lifecycle.open_saved_item_into_whiteboard(runtime=runtime, record_id=record.id)

    assert result.scope == "experiment"
    assert result.workspace.workspace_id == record.id
    assert result.workspace.path == tmp_path / "experiment" / "workspaces" / f"{record.id}.md"
    assert result.workspace.path.exists()
    assert not (tmp_path / "durable" / "workspaces" / f"{record.id}.md").exists()
    assert result.action.source == "memory"
    assert runtime.state_store.get_active_workspace_id(default_workspace_id="fallback") == record.id


def test_open_saved_item_into_whiteboard_raises_for_missing_record(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lifecycle = DraftArtifactLifecycle()

    with pytest.raises(FileNotFoundError):
        lifecycle.open_saved_item_into_whiteboard(runtime=runtime, record_id="missing-record")
