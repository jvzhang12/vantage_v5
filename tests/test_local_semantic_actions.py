from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactLifecycle
from vantage_v5.services.local_semantic_actions import LocalSemanticActionEngine
from vantage_v5.services.local_semantic_actions import LocalSemanticTurnContext
from vantage_v5.services.semantic_frame import SemanticFrame
from vantage_v5.storage.workspaces import WorkspaceDocument


def _workspace(tmp_path: Path, content: str) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id="draft",
        title="Draft",
        content=content,
        path=tmp_path / "draft.md",
        scenario_metadata=None,
    )


def test_policy_context_confirms_current_whiteboard_publish_target(tmp_path: Path) -> None:
    engine = LocalSemanticActionEngine(draft_artifact_lifecycle=DraftArtifactLifecycle())
    context = engine.policy_context(
        semantic_frame=SemanticFrame(
            user_goal="publish the current draft",
            task_type="artifact_publish",
            follow_up_type="new_request",
            target_surface="whiteboard",
            referenced_object=None,
            confidence=0.9,
        ),
        session=None,
        workspace=_workspace(tmp_path, "# Draft\n\nReady to publish."),
        workspace_scope="visible",
        pinned_context=None,
        pending_workspace_update=None,
        user_message="publish this artifact",
    )

    assert context.has_current_artifact is True
    assert context.publish_target_confirmed is True


def test_build_turn_parts_returns_clarification_for_ambiguous_local_action(tmp_path: Path) -> None:
    engine = LocalSemanticActionEngine(draft_artifact_lifecycle=DraftArtifactLifecycle())
    parts = engine.build_turn_parts(
        LocalSemanticTurnContext(
            runtime={"scope": "durable"},
            session=None,
            message="save this",
            history=[],
            workspace=_workspace(tmp_path, ""),
            workspace_scope="excluded",
            transient_workspace=False,
            semantic_frame={"task_type": "artifact_save"},
            semantic_policy={
                "action_type": "artifact_save",
                "should_clarify": True,
                "clarification_prompt": "What should I save?",
            },
            pinned_context_id=None,
            pinned_context=None,
        )
    )

    assert parts is not None
    assert parts.turn_body.mode == "clarification"
    assert parts.turn_body.assistant_message == "What should I save?"
    assert parts.experiment == {"active": False, "session_id": None, "saved_note_count": 0}


def test_build_turn_parts_answers_active_experiment_status(tmp_path: Path) -> None:
    @dataclass(frozen=True, slots=True)
    class FakeSession:
        session_id: str
        memories_dir: Path
        artifacts_dir: Path

    memories_dir = tmp_path / "memories"
    artifacts_dir = tmp_path / "artifacts"
    memories_dir.mkdir()
    artifacts_dir.mkdir()
    session = FakeSession(
        session_id="experiment-1",
        memories_dir=memories_dir,
        artifacts_dir=artifacts_dir,
    )
    engine = LocalSemanticActionEngine(draft_artifact_lifecycle=DraftArtifactLifecycle())

    parts = engine.build_turn_parts(
        LocalSemanticTurnContext(
            runtime={"scope": "experiment"},
            session=session,
            message="am I in experiment mode?",
            history=[],
            workspace=_workspace(tmp_path, ""),
            workspace_scope="excluded",
            transient_workspace=False,
            semantic_frame={"task_type": "experiment_management"},
            semantic_policy={"action_type": "experiment_manage", "should_clarify": False},
            pinned_context_id=None,
            pinned_context=None,
        )
    )

    assert parts is not None
    assert parts.turn_body.mode == "local_action"
    assert parts.turn_body.assistant_message == "Experiment mode is active, so temporary notes stay in this session."
    assert parts.experiment == {"active": True, "session_id": "experiment-1", "saved_note_count": 0}
