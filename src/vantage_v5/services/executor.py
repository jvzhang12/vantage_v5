from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vantage_v5.services.meta import MetaDecision
from vantage_v5.services.product_scope import ProductScope
from vantage_v5.services.product_scope import builtin_product_scope
from vantage_v5.services.product_scope import product_scope_for_record
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.overlay import get_overlay_record
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
    source_provenance: dict[str, Any] | None = None
    opened_copy: dict[str, Any] | None = None

    @property
    def concept_id(self) -> str | None:
        return self.record_id

    def to_dict(self) -> dict[str, Any]:
        payload = {
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
        if self.source_provenance is not None:
            payload["source_provenance"] = dict(self.source_provenance)
            payload.update(_flat_source_provenance_fields(self.source_provenance))
        if self.opened_copy is not None:
            payload["opened_copy"] = dict(self.opened_copy)
            payload.update(_flat_opened_copy_fields(self.opened_copy))
        return payload


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
        canonical_root: Path | None = None,
        experiment_root: Path | None = None,
        runtime_scope: str = "durable",
    ) -> None:
        self.concept_store = concept_store
        self.memory_store = memory_store
        self.artifact_store = artifact_store
        self.workspace_store = workspace_store
        self.state_store = state_store
        self.reference_concept_store = reference_concept_store
        self.reference_memory_store = reference_memory_store
        self.reference_artifact_store = reference_artifact_store
        self.canonical_root = canonical_root
        self.experiment_root = experiment_root
        self.runtime_scope = runtime_scope

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
        if getattr(record, "type", None) == "protocol":
            raise ValueError("Protocols are guidance objects and cannot be reopened as whiteboard drafts.")
        source_scope = _source_product_scope(
            record,
            canonical_root=self.canonical_root,
            experiment_root=self.experiment_root,
        )
        workspace_text = (
            f"# {record.title}\n\n"
            f"> {record.card}\n\n"
            f"{record.body.strip()}\n"
        )
        document = self.workspace_store.save(record.id, workspace_text)
        self.state_store.set_active_workspace_id(document.workspace_id)
        source_provenance = _source_provenance_payload(record, source_scope)
        opened_copy = _opened_copy_payload(
            document=document,
            source_provenance=source_provenance,
            copy_scope=_opened_copy_product_scope(self.runtime_scope),
        )
        return ExecutedAction(
            action="open_saved_item_into_workspace",
            status="executed",
            summary=f"Opened saved item '{record.title}' into the shared workspace.",
            record_id=record.id,
            workspace_id=document.workspace_id,
            source=record.source,
            record_title=record.title,
            source_provenance=source_provenance,
            opened_copy=opened_copy,
        )

    def open_concept_into_workspace(self, concept_id: str) -> ExecutedAction:
        return self.open_saved_item_into_workspace(concept_id)

    def _get_record(self, record_id: str):
        store_groups = [
            (self.concept_store, self.reference_concept_store),
            (self.memory_store, self.reference_memory_store),
            (self.artifact_store, self.reference_artifact_store),
        ]
        for stores in store_groups:
            try:
                return get_overlay_record(record_id, *stores)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"Saved item '{record_id}' was not found.")


def _source_product_scope(
    record: Any,
    *,
    canonical_root: Path | None,
    experiment_root: Path | None,
) -> ProductScope:
    if str(getattr(record, "source", "") or "").strip().lower() == "builtin":
        return builtin_product_scope()
    return product_scope_for_record(
        record,
        canonical_root=canonical_root,
        experiment_root=experiment_root,
        fallback_scope="durable",
    )


def _opened_copy_product_scope(runtime_scope: str) -> ProductScope:
    if runtime_scope == "experiment":
        return ProductScope(scope="experiment", durability="temporary")
    return ProductScope(scope="durable", durability="durable")


def _source_provenance_payload(record: Any, product_scope: ProductScope) -> dict[str, Any]:
    return {
        "relationship": "source_record",
        "record_id": record.id,
        "record_title": record.title,
        "source": record.source,
        "type": getattr(record, "type", None),
        **product_scope.to_payload(),
    }


def _opened_copy_payload(
    *,
    document: WorkspaceDocument,
    source_provenance: dict[str, Any],
    copy_scope: ProductScope,
) -> dict[str, Any]:
    return {
        "relationship": "editable_workspace_copy",
        "workspace_id": document.workspace_id,
        "source_record_id": source_provenance["record_id"],
        "source_record_title": source_provenance["record_title"],
        "source": source_provenance["source"],
        "source_scope": source_provenance["scope"],
        "writable": True,
        **copy_scope.to_payload(),
    }


def _flat_source_provenance_fields(source_provenance: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if "scope" in source_provenance:
        payload["source_scope"] = source_provenance["scope"]
    if "durability" in source_provenance:
        payload["source_durability"] = source_provenance["durability"]
    if "is_canonical" in source_provenance:
        payload["source_is_canonical"] = source_provenance["is_canonical"]
    return payload


def _flat_opened_copy_fields(opened_copy: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if "scope" in opened_copy:
        payload["opened_copy_scope"] = opened_copy["scope"]
    if "durability" in opened_copy:
        payload["opened_copy_durability"] = opened_copy["durability"]
    if "is_canonical" in opened_copy:
        payload["opened_copy_is_canonical"] = opened_copy["is_canonical"]
    if "writable" in opened_copy:
        payload["opened_copy_writable"] = opened_copy["writable"]
    return payload
