from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vantage_v5.services.record_cards import lineage_payload
from vantage_v5.services.record_cards import saved_record_scenario_metadata
from vantage_v5.services.record_cards import scenario_payload
from vantage_v5.storage.experiments import ExperimentSession
from vantage_v5.storage.memory_trace import parse_memory_trace_metadata
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(frozen=True, slots=True)
class ContextSourceResolver:
    """Resolve compact source summaries used during context preparation."""

    vault_store: VaultNoteStore

    def pinned_context_summary(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
        record_id: str | None,
    ) -> dict[str, Any] | None:
        if not record_id:
            return None
        stores = [
            (runtime["concept_store"], runtime["scope"]),
            (runtime["memory_store"], runtime["scope"]),
            (runtime["artifact_store"], runtime["scope"]),
            (durable_scope["concept_store"] if session is not None else None, "durable"),
            (durable_scope["memory_store"] if session is not None else None, "durable"),
            (durable_scope["artifact_store"] if session is not None else None, "durable"),
        ]
        for store, scope in stores:
            if store is None:
                continue
            try:
                record = store.get(record_id)
            except FileNotFoundError:
                continue
            return self._saved_record_summary(record, scope=scope)
        try:
            note = self.vault_store.get(record_id)
        except FileNotFoundError:
            return None
        return {
            "id": note.id,
            "title": note.title,
            "card": note.card,
            "type": note.type,
            "scenario_kind": None,
            "scenario": None,
            "source": "vault_note",
            "body_excerpt": note.body[:1200],
            "path": note.relative_path,
            "is_scenario_comparison": False,
        }

    def whiteboard_source_summary(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
        workspace_id: str | None,
    ) -> dict[str, Any] | None:
        if not workspace_id:
            return None
        summary = self.pinned_context_summary(durable_scope, session, runtime, workspace_id)
        if summary is None:
            return None
        return {
            "source_record_id": summary["id"],
            "source_record_title": summary["title"],
            "source": summary["source"],
            "type": summary.get("type"),
        }

    def navigator_continuity_context(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
        *,
        workspace: WorkspaceDocument,
        workspace_scope: str,
    ) -> dict[str, Any]:
        source_summary = self.whiteboard_source_summary(durable_scope, session, runtime, workspace.workspace_id)
        current_whiteboard = {
            "workspace_id": workspace.workspace_id,
            "title": workspace.title,
            "scope": workspace_scope,
            "in_scope": workspace_scope != "excluded",
            "has_content": bool(workspace.content.strip()),
            "content_excerpt": _single_line(workspace.content)[:240]
            if workspace_scope != "excluded" and workspace.content.strip()
            else "",
        }
        if source_summary is not None:
            current_whiteboard.update(source_summary)
        continuity = self._last_turn_continuity_context(durable_scope, session, runtime)
        continuity["current_whiteboard"] = current_whiteboard
        continuity["recent_whiteboards"] = self._recent_whiteboard_summaries(
            durable_scope,
            session,
            runtime,
            current_workspace_id=workspace.workspace_id,
            limit=3,
        )
        return continuity

    def _saved_record_summary(self, record: Any, *, scope: str) -> dict[str, Any]:
        scenario_metadata = saved_record_scenario_metadata(record)
        scenario = scenario_payload(scenario_metadata)
        payload = {
            "id": record.id,
            "title": record.title,
            "card": record.card,
            "type": record.type,
            "source": record.source,
            "scope": scope,
            "body_excerpt": record.body[:1200],
            "is_scenario_comparison": (
                scenario["scenario_kind"] == "comparison"
                or _is_scenario_comparison_record(record)
            ),
        }
        payload.update(lineage_payload(record))
        payload.update(scenario)
        return payload

    def _navigator_record_summary(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
        record_id: str | None,
    ) -> dict[str, Any] | None:
        summary = self.pinned_context_summary(durable_scope, session, runtime, record_id)
        if summary is None:
            return None
        return {
            "record_id": summary["id"],
            "title": summary["title"],
            "source": summary["source"],
            "type": summary.get("type"),
            "card": summary.get("card"),
            "reopenable_in_whiteboard": (
                summary.get("source") != "vault_note"
                and summary.get("type") != "protocol"
            ),
        }

    def _recent_whiteboard_summaries(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
        *,
        current_workspace_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        workspaces_dir = runtime["workspace_store"].workspaces_dir
        candidates: list[tuple[float, Path]] = []
        for path in workspaces_dir.glob("*.md"):
            try:
                modified_at = path.stat().st_mtime
            except OSError:
                continue
            candidates.append((modified_at, path))
        candidates.sort(key=lambda item: (item[0], item[1].name), reverse=True)

        summaries: list[dict[str, Any]] = []
        for modified_at, path in candidates:
            workspace_id = path.stem
            if workspace_id == current_workspace_id:
                continue
            try:
                document = runtime["workspace_store"].load(workspace_id)
            except FileNotFoundError:
                continue
            source_summary = self.whiteboard_source_summary(durable_scope, session, runtime, workspace_id)
            kind = "whiteboard"
            if (document.scenario_metadata or {}).get("scenario_kind") == "branch":
                kind = "scenario_branch"
            elif source_summary is not None:
                kind = "reopened_saved_item"
            summary = {
                "workspace_id": document.workspace_id,
                "title": document.title,
                "kind": kind,
                "last_active_at": _isoformat_utc(modified_at),
                "content_excerpt": _single_line(document.content)[:240] if document.content.strip() else "",
            }
            if source_summary is not None:
                summary.update(source_summary)
            summaries.append(summary)
            if len(summaries) >= limit:
                break
        return summaries

    def _last_turn_continuity_context(
        self,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
        runtime: dict[str, Any],
    ) -> dict[str, Any]:
        traces = runtime["memory_trace_store"].list_recent_traces(limit=6)
        if not traces:
            return {
                "last_turn_referenced_record": None,
                "last_turn_recall": [],
            }
        latest = traces[0]
        metadata = parse_memory_trace_metadata(latest)
        raw_metadata = dict(latest.metadata) if isinstance(getattr(latest, "metadata", {}), dict) else {}
        recall_items: list[dict[str, Any]] = []
        for record_id in metadata.get("recalled_ids", [])[:3]:
            summary = self._navigator_record_summary(durable_scope, session, runtime, record_id)
            if summary is not None:
                recall_items.append(summary)

        referenced_record = None
        referenced_record_id = str(raw_metadata.get("referenced_record_id") or "").strip()
        if referenced_record_id:
            referenced_record = self._navigator_record_summary(durable_scope, session, runtime, referenced_record_id)
        preserved_context_id = metadata.get("preserved_context_id")
        if referenced_record is None and preserved_context_id:
            referenced_record = self._navigator_record_summary(durable_scope, session, runtime, preserved_context_id)
        if referenced_record is None:
            reopenable = [item for item in recall_items if item.get("reopenable_in_whiteboard")]
            if len(reopenable) == 1:
                referenced_record = reopenable[0]
        return {
            "last_turn_referenced_record": referenced_record,
            "last_turn_recall": recall_items,
        }


def _isoformat_utc(value: float | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _is_scenario_comparison_record(record: Any) -> bool:
    if getattr(record, "type", None) == "scenario_comparison":
        return True
    body = getattr(record, "body", "")
    return "## Recommendation" in body and "## Branches Compared" in body
