from __future__ import annotations

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
) -> dict[str, Any] | None:
    metadata = dict(parse_scenario_metadata_block(body) or {})
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
    scenario_kind = str(metadata.get("scenario_kind") or "").strip().lower()
    if scenario_kind != "comparison":
        return None
    branch_workspace_ids = metadata.get("branch_workspace_ids")
    if not isinstance(branch_workspace_ids, list) or not branch_workspace_ids:
        branch_workspace_ids = _parse_branches_compared(body)
    if not branch_workspace_ids and comes_from:
        branch_workspace_ids = [value for value in comes_from[1:] if str(value).strip()]
    metadata["branch_workspace_ids"] = [str(value).strip() for value in branch_workspace_ids if str(value).strip()]
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


def _namespace_from_branch_ids(branch_workspace_ids: list[str]) -> str:
    namespaces = {workspace_id.rsplit("--", 1)[0] for workspace_id in branch_workspace_ids if "--" in workspace_id}
    if len(namespaces) == 1:
        return next(iter(namespaces))
    return ""


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
        if scenario_metadata:
            kwargs["body"] = inject_scenario_metadata(kwargs.get("body", ""), scenario_metadata)
        if record_id is None:
            return self.create_record(**kwargs)
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
        )

    @staticmethod
    def parse_scenario_metadata(record: ArtifactRecord) -> dict[str, Any] | None:
        return parse_artifact_scenario_metadata(
            record.body,
            record_id=record.id,
            record_type=record.type,
            comes_from=record.comes_from,
        )
