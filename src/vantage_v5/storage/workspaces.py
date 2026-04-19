from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


SCENARIO_METADATA_HEADING = "## Scenario Metadata"
_WORKSPACE_FIELD_RE = re.compile(r"^(Base Workspace|Question|Branch Label|Comparison Artifact|Scenario Namespace):\s*(.+?)\s*$")


@dataclass(slots=True)
class WorkspaceDocument:
    workspace_id: str
    title: str
    content: str
    path: Path
    scenario_metadata: dict[str, Any] | None = None


def format_scenario_metadata_block(metadata: dict[str, Any]) -> str:
    lines = [SCENARIO_METADATA_HEADING]
    for key, value in metadata.items():
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"- {key}:")
            for item in value:
                cleaned = str(item).strip()
                if cleaned:
                    lines.append(f"  - {cleaned}")
            continue
        cleaned = str(value).strip()
        if cleaned:
            lines.append(f"- {key}: {cleaned}")
    return "\n".join(lines)


def inject_scenario_metadata(content: str, metadata: dict[str, Any]) -> str:
    block = format_scenario_metadata_block(metadata).strip()
    stripped = content.strip()
    if not stripped:
        return f"{block}\n"
    lines = stripped.splitlines()
    if lines[0].startswith("# "):
        remainder = "\n".join(lines[1:]).lstrip("\n")
        if remainder:
            return f"{lines[0]}\n\n{block}\n\n{remainder}\n"
        return f"{lines[0]}\n\n{block}\n"
    return f"{block}\n\n{stripped}\n"


def parse_scenario_metadata_block(content: str) -> dict[str, Any] | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != SCENARIO_METADATA_HEADING:
            continue
        metadata: dict[str, Any] = {}
        active_list_key: str | None = None
        for raw_line in lines[index + 1 :]:
            stripped = raw_line.strip()
            if not stripped:
                active_list_key = None
                continue
            if stripped.startswith("## "):
                break
            if active_list_key and raw_line.startswith("  - "):
                value = raw_line[4:].strip()
                if value:
                    metadata.setdefault(active_list_key, []).append(value)
                continue
            if not stripped.startswith("- "):
                active_list_key = None
                continue
            key, separator, value = stripped[2:].partition(":")
            if not separator:
                active_list_key = None
                continue
            normalized_key = key.strip()
            cleaned_value = value.strip()
            if cleaned_value:
                metadata[normalized_key] = cleaned_value
                active_list_key = None
            else:
                metadata[normalized_key] = []
                active_list_key = normalized_key
        return metadata or None
    return None


def parse_workspace_scenario_metadata(content: str, *, workspace_id: str | None = None) -> dict[str, Any] | None:
    metadata = dict(parse_scenario_metadata_block(content) or {})
    for line in content.splitlines():
        match = _WORKSPACE_FIELD_RE.match(line.strip())
        if not match:
            continue
        label, value = match.groups()
        if label == "Base Workspace":
            metadata.setdefault("base_workspace_id", value.strip())
        elif label == "Question":
            metadata.setdefault("comparison_question", value.strip())
        elif label == "Branch Label":
            metadata.setdefault("branch_label", value.strip())
        elif label == "Comparison Artifact":
            metadata.setdefault("comparison_artifact_id", value.strip())
        elif label == "Scenario Namespace":
            namespace_value = value.strip()
            namespace_id = namespace_value
            namespace_mode = ""
            if namespace_value.endswith(")") and " (" in namespace_value:
                namespace_id, _, trailing = namespace_value.rpartition(" (")
                namespace_mode = trailing.rstrip(")").strip()
            metadata.setdefault("scenario_namespace_id", namespace_id.strip())
            if namespace_mode:
                metadata.setdefault("namespace_mode", namespace_mode)
    if "Status: Counterfactual Branch" in content:
        metadata.setdefault("scenario_kind", "branch")
    if workspace_id and "--" in workspace_id:
        metadata.setdefault("scenario_namespace_id", workspace_id.rsplit("--", 1)[0])
    if metadata.get("scenario_namespace_id") and metadata.get("base_workspace_id"):
        metadata.setdefault(
            "namespace_mode",
            "anchored" if metadata["scenario_namespace_id"] == metadata["base_workspace_id"] else "detached",
        )
    scenario_kind = str(metadata.get("scenario_kind") or "").strip().lower()
    if scenario_kind != "branch":
        return None
    branch_workspace_metadata = {
        "scenario_kind": "branch",
        "base_workspace_id": str(metadata.get("base_workspace_id") or "").strip(),
        "comparison_question": str(metadata.get("comparison_question") or "").strip(),
        "branch_label": str(metadata.get("branch_label") or "").strip(),
        "comparison_artifact_id": str(metadata.get("comparison_artifact_id") or "").strip(),
        "scenario_namespace_id": str(metadata.get("scenario_namespace_id") or "").strip(),
        "namespace_mode": str(metadata.get("namespace_mode") or "").strip().lower(),
    }
    return {
        key: value
        for key, value in branch_workspace_metadata.items()
        if value
    } or None


class WorkspaceStore:
    def __init__(self, workspaces_dir: Path) -> None:
        self.workspaces_dir = workspaces_dir

    def load(self, workspace_id: str) -> WorkspaceDocument:
        path = self.workspaces_dir / f"{workspace_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"Workspace '{workspace_id}' was not found.")
        content = path.read_text(encoding="utf-8")
        title = self._title_from_content(workspace_id, content)
        return WorkspaceDocument(
            workspace_id=workspace_id,
            title=title,
            content=content,
            path=path,
            scenario_metadata=parse_workspace_scenario_metadata(content, workspace_id=workspace_id),
        )

    def save(self, workspace_id: str, content: str) -> WorkspaceDocument:
        path = self.workspaces_dir / f"{workspace_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = self.load(workspace_id)
            metadata_block = parse_scenario_metadata_block(content)
            if (
                existing.scenario_metadata
                and existing.scenario_metadata.get("scenario_kind") == "branch"
                and metadata_block is None
            ):
                content = inject_scenario_metadata(content, existing.scenario_metadata)
        path.write_text(content, encoding="utf-8")
        return self.load(workspace_id)

    @staticmethod
    def _title_from_content(workspace_id: str, content: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return workspace_id.replace("-", " ").title()

    @staticmethod
    def parse_scenario_metadata(content: str, *, workspace_id: str | None = None) -> dict[str, Any] | None:
        return parse_workspace_scenario_metadata(content, workspace_id=workspace_id)
