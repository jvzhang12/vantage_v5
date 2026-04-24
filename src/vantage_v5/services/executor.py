from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vantage_v5.services.meta import MetaDecision
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


@dataclass(slots=True)
class ExecutedAction:
    action: str
    status: str
    summary: str
    record_id: str | None = None
    workspace_id: str | None = None
    source: str | None = None
    record_title: str | None = None

    @property
    def concept_id(self) -> str | None:
        return self.record_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.action,
            "action": self.action,
            "status": self.status,
            "summary": self.summary,
            "record_id": self.record_id,
            "concept_id": self.concept_id,
            "workspace_id": self.workspace_id,
            "source": self.source,
            "record_title": self.record_title,
            "concept_title": self.record_title,
        }


class GraphActionExecutor:
    def __init__(
        self,
        *,
        concept_store: ConceptStore,
        memory_store: MemoryStore,
        artifact_store: ArtifactStore,
        workspace_store: WorkspaceStore,
        state_store: ActiveWorkspaceStateStore,
        reference_concept_store: ConceptStore | None = None,
        reference_memory_store: MemoryStore | None = None,
        reference_artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.concept_store = concept_store
        self.memory_store = memory_store
        self.artifact_store = artifact_store
        self.workspace_store = workspace_store
        self.state_store = state_store
        self.reference_concept_store = reference_concept_store
        self.reference_memory_store = reference_memory_store
        self.reference_artifact_store = reference_artifact_store

    def execute(
        self,
        decision: MetaDecision,
        *,
        workspace: WorkspaceDocument,
    ) -> ExecutedAction | None:
        action = decision.action
        if action == "no_op":
            return None

        if action == "create_concept":
            concept = self.concept_store.create_concept(
                title=decision.title or workspace.title,
                card=decision.card or workspace.title,
                body=decision.body or "",
                links_to=decision.links_to or [],
            )
            return ExecutedAction(
                action=action,
                status="executed",
                summary=f"Created concept '{concept.title}'.",
                record_id=concept.id,
                source="concept",
                record_title=concept.title,
            )

        if action == "create_memory":
            memory = self.memory_store.create_memory(
                title=decision.title or workspace.title,
                card=decision.card or workspace.title,
                body=decision.body or "",
                links_to=decision.links_to or [],
            )
            return ExecutedAction(
                action=action,
                status="executed",
                summary=f"Created memory '{memory.title}'.",
                record_id=memory.id,
                source="memory",
                record_title=memory.title,
            )

        if action == "create_revision":
            if not decision.target_concept_id:
                return ExecutedAction(
                    action=action,
                    status="skipped",
                    summary="Revision was requested without a target id.",
                )
            try:
                concept = self.concept_store.create_revision(
                    base_concept_id=decision.target_concept_id,
                    title=decision.title or "Revision",
                    card=decision.card or "Revision of an existing concept.",
                    body=decision.body or "",
                    links_to=decision.links_to or [],
                )
            except FileNotFoundError:
                return ExecutedAction(
                    action=action,
                    status="skipped",
                    summary="Revision target was not found in the concept store.",
                )
            return ExecutedAction(
                action=action,
                status="executed",
                summary=f"Created revision '{concept.title}'.",
                record_id=concept.id,
                source="concept",
                record_title=concept.title,
            )

        if action == "promote_workspace_to_artifact":
            artifact = self.artifact_store.create_artifact(
                title=decision.title or workspace.title,
                card=decision.card or workspace.title,
                body=decision.body or workspace.content,
                links_to=decision.links_to or [],
                comes_from=[workspace.workspace_id],
                metadata={
                    "artifact_origin": "whiteboard",
                    "artifact_lifecycle": "promoted_artifact",
                },
            )
            return ExecutedAction(
                action=action,
                status="executed",
                summary=f"Promoted workspace '{workspace.title}' into artifact '{artifact.title}'.",
                record_id=artifact.id,
                workspace_id=workspace.workspace_id,
                source="artifact",
                record_title=artifact.title,
            )

        return ExecutedAction(
            action=action,
            status="skipped",
            summary=f"Action '{action}' is not supported.",
        )

    def promote_workspace(
        self,
        *,
        workspace: WorkspaceDocument,
        title: str | None = None,
        card: str | None = None,
    ) -> ExecutedAction:
        artifact = self.artifact_store.create_artifact(
            title=title or workspace.title,
            card=card or workspace.title,
            body=workspace.content,
            comes_from=[workspace.workspace_id],
            metadata={
                "artifact_origin": "whiteboard",
                "artifact_lifecycle": "promoted_artifact",
            },
        )
        return ExecutedAction(
            action="promote_workspace_to_artifact",
            status="executed",
            summary=f"Promoted workspace '{workspace.title}' into artifact '{artifact.title}'.",
            record_id=artifact.id,
            workspace_id=workspace.workspace_id,
            source="artifact",
            record_title=artifact.title,
        )

    def save_workspace_iteration_artifact(
        self,
        *,
        workspace: WorkspaceDocument,
        title: str | None = None,
        card: str | None = None,
        body: str | None = None,
    ) -> ExecutedAction:
        artifact = self.artifact_store.create_artifact(
            title=title or workspace.title,
            card=card or title or workspace.title,
            body=body or workspace.content,
            comes_from=[workspace.workspace_id],
            metadata={
                "artifact_origin": "whiteboard",
                "artifact_lifecycle": "whiteboard_snapshot",
            },
        )
        return ExecutedAction(
            action="save_workspace_iteration_artifact",
            status="executed",
            summary=f"Saved whiteboard iteration '{workspace.title}' as artifact '{artifact.title}'.",
            record_id=artifact.id,
            workspace_id=workspace.workspace_id,
            source="artifact",
            record_title=artifact.title,
        )

    def open_saved_item_into_workspace(self, record_id: str) -> ExecutedAction:
        record = self._get_record(record_id)
        workspace_text = (
            f"# {record.title}\n\n"
            f"> {record.card}\n\n"
            f"{record.body.strip()}\n"
        )
        document = self.workspace_store.save(record.id, workspace_text)
        self.state_store.set_active_workspace_id(document.workspace_id)
        return ExecutedAction(
            action="open_saved_item_into_workspace",
            status="executed",
            summary=f"Opened saved item '{record.title}' into the shared workspace.",
            record_id=record.id,
            workspace_id=document.workspace_id,
            source=record.source,
            record_title=record.title,
        )

    def open_concept_into_workspace(self, concept_id: str) -> ExecutedAction:
        return self.open_saved_item_into_workspace(concept_id)

    def _get_record(self, record_id: str):
        stores = [
            self.concept_store,
            self.memory_store,
            self.artifact_store,
            self.reference_concept_store,
            self.reference_memory_store,
            self.reference_artifact_store,
        ]
        for store in stores:
            if store is None:
                continue
            try:
                return store.get(record_id)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"Saved item '{record_id}' was not found.")
