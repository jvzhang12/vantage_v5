from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vantage_v5.services.executor import ExecutedAction
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.artifacts import parse_artifact_lifecycle_metadata
from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


def artifact_lifecycle_card_fields(record: Any) -> dict[str, str]:
    """Return UI-facing lifecycle fields for artifact cards only."""
    if getattr(record, "source", None) != "artifact":
        return {}
    return parse_artifact_lifecycle_metadata(record)


def artifact_lifecycle_kind(record: Any) -> str:
    return artifact_lifecycle_card_fields(record).get("artifact_lifecycle", "")


@dataclass(frozen=True, slots=True)
class DraftArtifactRuntime:
    workspace_store: WorkspaceStore
    artifact_store: ArtifactStore
    state_store: ActiveWorkspaceStateStore
    executor: GraphActionExecutor
    scope: str

    @classmethod
    def from_mapping(cls, runtime: dict[str, Any]) -> DraftArtifactRuntime:
        return cls(
            workspace_store=runtime["workspace_store"],
            artifact_store=runtime["artifact_store"],
            state_store=runtime["state_store"],
            executor=runtime["executor"],
            scope=str(runtime["scope"]),
        )


@dataclass(frozen=True, slots=True)
class DraftArtifactLifecycleResult:
    workspace: WorkspaceDocument
    action: ExecutedAction
    artifact: MarkdownRecord | None
    scope: str
    assistant_message: str | None = None

    @property
    def graph_action(self) -> dict[str, Any]:
        return self.action.to_dict()


class DraftArtifactLifecycle:
    def open_saved_item_into_whiteboard(
        self,
        *,
        runtime: DraftArtifactRuntime,
        record_id: str,
    ) -> DraftArtifactLifecycleResult:
        normalized_record_id = record_id.strip()
        if not normalized_record_id:
            raise ValueError("record_id is required.")
        action = runtime.executor.open_saved_item_into_workspace(normalized_record_id)
        workspace_id = action.workspace_id or normalized_record_id
        workspace = runtime.workspace_store.load(workspace_id)
        return DraftArtifactLifecycleResult(
            workspace=workspace,
            action=action,
            artifact=None,
            scope=runtime.scope,
        )

    def save_visible_whiteboard_snapshot(
        self,
        *,
        runtime: DraftArtifactRuntime,
        workspace: WorkspaceDocument,
    ) -> DraftArtifactLifecycleResult:
        document = runtime.workspace_store.save(workspace.workspace_id, workspace.content)
        runtime.state_store.set_active_workspace_id(document.workspace_id)
        action = runtime.executor.save_workspace_iteration_artifact(workspace=document)
        artifact = runtime.artifact_store.get(action.record_id) if action.record_id else None
        return DraftArtifactLifecycleResult(
            workspace=document,
            action=action,
            artifact=artifact,
            scope=runtime.scope,
            assistant_message=f"I saved {document.title} as a whiteboard snapshot.",
        )

    def publish_visible_whiteboard(
        self,
        *,
        runtime: DraftArtifactRuntime,
        workspace: WorkspaceDocument,
    ) -> DraftArtifactLifecycleResult:
        action = runtime.executor.promote_workspace(workspace=workspace)
        artifact = runtime.artifact_store.get(action.record_id) if action.record_id else None
        return DraftArtifactLifecycleResult(
            workspace=workspace,
            action=action,
            artifact=artifact,
            scope=runtime.scope,
            assistant_message=f"I published {workspace.title} as a reusable artifact.",
        )

    def save_workspace_update(
        self,
        *,
        runtime: DraftArtifactRuntime,
        workspace_id: str,
        content: str,
    ) -> DraftArtifactLifecycleResult:
        document = runtime.workspace_store.save(workspace_id, content)
        runtime.state_store.set_active_workspace_id(document.workspace_id)
        action = runtime.executor.save_workspace_iteration_artifact(workspace=document)
        artifact = runtime.artifact_store.get(action.record_id) if action.record_id else None
        return DraftArtifactLifecycleResult(
            workspace=document,
            action=action,
            artifact=artifact,
            scope=runtime.scope,
        )

    def promote_whiteboard_to_artifact(
        self,
        *,
        runtime: DraftArtifactRuntime,
        workspace_id: str,
        content: str | None = None,
        title: str | None = None,
        card: str | None = None,
    ) -> DraftArtifactLifecycleResult:
        workspace = self._workspace_for_promotion(
            runtime=runtime,
            workspace_id=workspace_id,
            content=content,
        )
        action = runtime.executor.promote_workspace(
            workspace=workspace,
            title=title,
            card=card,
        )
        artifact = runtime.artifact_store.get(action.record_id) if action.record_id else None
        return DraftArtifactLifecycleResult(
            workspace=workspace,
            action=action,
            artifact=artifact,
            scope=runtime.scope,
        )

    def _workspace_for_promotion(
        self,
        *,
        runtime: DraftArtifactRuntime,
        workspace_id: str,
        content: str | None,
    ) -> WorkspaceDocument:
        try:
            workspace = runtime.workspace_store.load(workspace_id)
        except FileNotFoundError:
            if content is None:
                raise
            return self._workspace_from_unsaved_buffer(runtime.workspace_store, workspace_id, content)
        if content is not None:
            return self._workspace_from_buffer(workspace, content)
        return workspace

    @staticmethod
    def _workspace_from_buffer(document: WorkspaceDocument, content: str) -> WorkspaceDocument:
        scenario_metadata = WorkspaceStore.parse_scenario_metadata(content, workspace_id=document.workspace_id)
        return WorkspaceDocument(
            workspace_id=document.workspace_id,
            title=WorkspaceStore._title_from_content(document.workspace_id, content),
            content=content,
            path=document.path,
            scenario_metadata=scenario_metadata or document.scenario_metadata,
        )

    @staticmethod
    def _workspace_from_unsaved_buffer(
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
