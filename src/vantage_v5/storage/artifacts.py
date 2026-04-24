from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.markdown_store import MarkdownRecordStore
from vantage_v5.storage.markdown_store import slugify
from vantage_v5.storage.workspaces import inject_scenario_metadata
from vantage_v5.storage.workspaces import parse_scenario_metadata_block


ArtifactRecord = MarkdownRecord
_ARTIFACT_FIELD_RE = re.compile(r"^(Base Workspace|Question):\s*(.+?)\s*$")


def parse_artifact_scenario_metadata(
    body: str,
    *,
    record_id: str | None = None,
    record_type: str | None = None,
    comes_from: list[str] | None = None,
    record_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    metadata = dict(record_metadata or {})
    body_metadata = parse_scenario_metadata_block(body) or {}
    for key, value in body_metadata.items():
        metadata.setdefault(key, value)
    if record_type == "scenario_comparison":
        metadata.setdefault("scenario_kind", "comparison")
    for line in body.splitlines():
        match = _ARTIFACT_FIELD_RE.match(line.strip())
        if not match:
            continue
        label, value = match.groups()
        if label == "Base Workspace":
            metadata.setdefault("base_workspace_id", value.strip())
        elif label == "Question":
            metadata.setdefault("comparison_question", value.strip())
    if not metadata.get("scenario_kind") and _looks_like_legacy_comparison_artifact(
        body,
        metadata=metadata,
        comes_from=comes_from,
    ):
        metadata["scenario_kind"] = "comparison"
    scenario_kind = str(metadata.get("scenario_kind") or "").strip().lower()
    if scenario_kind != "comparison":
        return None
    branch_index = _normalize_branch_index(metadata.get("branch_index"))
    if not branch_index:
        branch_index = _parse_branch_index(body)
    branch_workspace_ids = _normalize_branch_workspace_ids(metadata.get("branch_workspace_ids"))
    if not branch_workspace_ids and branch_index:
        branch_workspace_ids = [entry["workspace_id"] for entry in branch_index if entry.get("workspace_id")]
    if not branch_workspace_ids:
        branch_workspace_ids = _parse_branches_compared(body)
    if not branch_workspace_ids and comes_from:
        branch_workspace_ids = [value for value in comes_from[1:] if str(value).strip()]
    metadata["branch_workspace_ids"] = [str(value).strip() for value in branch_workspace_ids if str(value).strip()]
    if branch_index:
        metadata["branch_index"] = branch_index
    if not metadata.get("base_workspace_id") and comes_from:
        metadata["base_workspace_id"] = str(comes_from[0]).strip()
    if record_id:
        metadata.setdefault("comparison_artifact_id", record_id)
    if not metadata.get("scenario_namespace_id"):
        namespace_id = _namespace_from_branch_ids(metadata["branch_workspace_ids"])
        if namespace_id:
            metadata["scenario_namespace_id"] = namespace_id
    if metadata.get("scenario_namespace_id") and metadata.get("base_workspace_id"):
        metadata.setdefault(
            "namespace_mode",
            "anchored" if metadata["scenario_namespace_id"] == metadata["base_workspace_id"] else "detached",
        )
    comparison_metadata = {
        "scenario_kind": "comparison",
        "base_workspace_id": str(metadata.get("base_workspace_id") or "").strip(),
        "comparison_question": str(metadata.get("comparison_question") or "").strip(),
        "comparison_artifact_id": str(metadata.get("comparison_artifact_id") or "").strip(),
        "branch_workspace_ids": metadata["branch_workspace_ids"],
        "branch_index": metadata.get("branch_index", []),
        "scenario_namespace_id": str(metadata.get("scenario_namespace_id") or "").strip(),
        "namespace_mode": str(metadata.get("namespace_mode") or "").strip().lower(),
    }
    filtered: dict[str, Any] = {}
    for key, value in comparison_metadata.items():
        if isinstance(value, list):
            if value:
                filtered[key] = value
            continue
        if value:
            filtered[key] = value
    return filtered or None


def _parse_branches_compared(body: str) -> list[str]:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "## Branches Compared":
            continue
        branch_ids: list[str] = []
        for raw_line in lines[index + 1 :]:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if value:
                    branch_ids.append(value)
        return branch_ids
    return []


def _parse_branch_index(body: str) -> list[dict[str, Any]]:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "## Branch Index":
            continue
        branch_index: list[dict[str, Any]] = []
        for raw_line in lines[index + 1 :]:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                break
            if not stripped.startswith("- "):
                continue
            candidate = stripped[2:].strip()
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            normalized = _normalize_branch_index_entry(parsed)
            if normalized:
                branch_index.append(normalized)
        return branch_index
    return []


def _normalize_branch_index(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        branch = _normalize_branch_index_entry(item)
        if branch:
            normalized.append(branch)
    return normalized


def _normalize_branch_index_entry(value: dict[str, Any]) -> dict[str, Any] | None:
    workspace_id = str(
        value.get("workspace_id")
        or value.get("branch_workspace_id")
        or value.get("id")
        or ""
    ).strip()
    if not workspace_id:
        return None
    normalized: dict[str, Any] = {"workspace_id": workspace_id}
    title = str(value.get("title") or "").strip()
    if title:
        normalized["title"] = title
    label = str(value.get("label") or value.get("branch_label") or "").strip()
    if label:
        normalized["label"] = label
    summary = str(value.get("summary") or value.get("card") or "").strip()
    if summary:
        normalized["summary"] = summary
    return normalized


def _normalize_branch_workspace_ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _looks_like_legacy_comparison_artifact(
    body: str,
    *,
    metadata: dict[str, Any],
    comes_from: list[str] | None,
) -> bool:
    normalized_body = body or ""
    if "## Branches Compared" not in normalized_body:
        return False
    if "## Recommendation" in normalized_body:
        return True
    if metadata.get("comparison_question") or metadata.get("base_workspace_id"):
        return True
    if comes_from and len([value for value in comes_from if str(value).strip()]) > 1:
        return True
    return False


def _namespace_from_branch_ids(branch_workspace_ids: list[str]) -> str:
    namespaces = {workspace_id.rsplit("--", 1)[0] for workspace_id in branch_workspace_ids if "--" in workspace_id}
    if len(namespaces) == 1:
        return next(iter(namespaces))
    return ""


def parse_artifact_lifecycle_metadata(record: ArtifactRecord) -> dict[str, str]:
    metadata = dict(record.metadata) if isinstance(record.metadata, dict) else {}
    scenario_metadata = ArtifactStore.parse_scenario_metadata(record) or {}
    lifecycle = str(metadata.get("artifact_lifecycle") or "").strip().lower()
    origin = str(metadata.get("artifact_origin") or "").strip().lower()

    if str(scenario_metadata.get("scenario_kind") or "").strip().lower() == "comparison":
        lifecycle = lifecycle or "comparison_hub"
        origin = origin or "scenario_lab"

    if not lifecycle:
        lifecycle = "artifact"

    if not origin:
        if lifecycle in {"whiteboard_snapshot", "promoted_artifact"}:
            origin = "whiteboard"
        elif lifecycle == "comparison_hub":
            origin = "scenario_lab"
        else:
            origin = "library"

    return {
        "artifact_lifecycle": lifecycle,
        "artifact_origin": origin,
    }


class ArtifactStore(MarkdownRecordStore):
    def __init__(self, artifacts_dir: Path) -> None:
        super().__init__(
            artifacts_dir,
            source="artifact",
            default_type="artifact",
            trust="medium",
        )

    def list_artifacts(self) -> list[ArtifactRecord]:
        return self.list_records()

    def preview_artifact_id(self, title: str, *, record_type: str | None = None) -> str:
        fallback = slugify(record_type or self.default_type)
        return self._unique_id(slugify(title) or fallback or self.default_type)

    def create_artifact(self, **kwargs) -> ArtifactRecord:
        record_id = kwargs.pop("record_id", None)
        scenario_metadata = kwargs.pop("scenario_metadata", None)
        record_metadata = kwargs.pop("metadata", None)
        combined_metadata: dict[str, Any] | None = None
        if isinstance(record_metadata, dict):
            combined_metadata = dict(record_metadata)
        if isinstance(scenario_metadata, dict):
            if combined_metadata is None:
                combined_metadata = {}
            combined_metadata.update(scenario_metadata)
        if scenario_metadata:
            kwargs["body"] = inject_scenario_metadata(
                kwargs.get("body", ""),
                _body_scenario_metadata(scenario_metadata),
            )
        if record_id is None:
            return self.create_record(metadata=combined_metadata, **kwargs)
        path = self.records_dir / f"{record_id}.md"
        if path.exists():
            raise FileExistsError(f"Artifact '{record_id}' already exists.")
        return self._write_record(
            record_id=record_id,
            title=(kwargs.get("title") or "").strip() or record_id.replace("-", " ").title(),
            card=(kwargs.get("card") or "").strip(),
            body=(kwargs.get("body") or "").strip(),
            type=kwargs.get("type") or self.default_type,
            links_to=list(kwargs.get("links_to") or []),
            comes_from=list(kwargs.get("comes_from") or []),
            status=kwargs.get("status", "active"),
            metadata=combined_metadata,
        )

    @staticmethod
    def parse_scenario_metadata(record: ArtifactRecord) -> dict[str, Any] | None:
        return parse_artifact_scenario_metadata(
            record.body,
            record_id=record.id,
            record_type=record.type,
            comes_from=record.comes_from,
            record_metadata=record.metadata,
        )


def _body_scenario_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if key != "branch_index"}
