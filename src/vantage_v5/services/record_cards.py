from __future__ import annotations

import re
from typing import Any

from vantage_v5.services.draft_artifact_lifecycle import artifact_lifecycle_card_fields
from vantage_v5.services.protocols import BUILT_IN_PROTOCOLS
from vantage_v5.storage.artifacts import ArtifactStore


def lineage_payload(record: Any) -> dict[str, Any]:
    comes_from = list(getattr(record, "comes_from", []) or [])
    links_to = list(getattr(record, "links_to", []) or [])
    record_id = str(getattr(record, "id", "") or "")
    record_source = str(getattr(record, "source", "") or "")
    metadata = getattr(record, "metadata", {}) if isinstance(getattr(record, "metadata", {}), dict) else {}
    explicit_revision_parent = str(metadata.get("revision_of", "") or "").strip() or None
    inferred_revision_parent = comes_from[0] if comes_from else None
    revision_parent_id = explicit_revision_parent or (
        inferred_revision_parent
        if record_source == "concept" and bool(comes_from) and bool(re.search(r"--v\d+$", record_id))
        else None
    )
    return {
        "links_to": links_to,
        "comes_from": comes_from,
        "derived_from_id": comes_from[0] if comes_from else None,
        "revision_parent_id": revision_parent_id,
        "lineage_kind": "revision" if revision_parent_id else ("provenance" if comes_from else "none"),
    }


def serialize_concept_card(concept: Any, *, scope: str = "durable") -> dict[str, Any]:
    metadata = getattr(concept, "metadata", {}) if isinstance(getattr(concept, "metadata", {}), dict) else {}
    payload = {
        "id": concept.id,
        "title": concept.title,
        "type": concept.type,
        "card": concept.card,
        "body": concept.body,
        "status": concept.status,
        "source": "concept",
        "source_label": "Experiment concepts" if scope == "experiment" else "Concept KB",
        "trust": "high",
        "kind": "concept",
        "memory_role": "semantic_knowledge",
        "recall_status": "available",
        "source_tier": "curated",
        "scope": scope,
        "filename": concept.path.name,
    }
    if concept.type == "protocol":
        payload["kind"] = "protocol"
        payload["memory_role"] = "protocol"
        payload["source_tier"] = "instruction"
        payload["protocol"] = {
            "protocol_kind": metadata.get("protocol_kind"),
            "variables": metadata.get("variables") or {},
            "applies_to": metadata.get("applies_to") or [],
            "modifiable": bool(metadata.get("modifiable", True)),
            "is_builtin": False,
            "overrides_builtin": bool(metadata.get("override_of_builtin")),
        }
    payload.update(lineage_payload(concept))
    return payload


def serialize_built_in_protocol_card(protocol_kind: str) -> dict[str, Any]:
    built_in = BUILT_IN_PROTOCOLS[protocol_kind]
    return {
        "id": built_in["id"],
        "title": built_in["title"],
        "type": "protocol",
        "card": built_in["card"],
        "body": built_in["body"],
        "status": "active",
        "source": "concept",
        "source_label": "Built-in protocols",
        "trust": "high",
        "kind": "protocol",
        "memory_role": "protocol",
        "recall_status": "available",
        "source_tier": "instruction",
        "scope": "builtin",
        "filename": None,
        "links_to": [],
        "comes_from": [],
        "derived_from_id": None,
        "revision_parent_id": None,
        "lineage_kind": "none",
        "protocol": {
            "protocol_kind": protocol_kind,
            "variables": built_in.get("variables") or {},
            "applies_to": built_in.get("applies_to") or [],
            "modifiable": True,
            "is_builtin": True,
            "overrides_builtin": False,
        },
    }


def serialize_saved_note_card(record: Any, *, scope: str = "durable") -> dict[str, Any]:
    source_label = {
        "memory": "Experiment memories" if scope == "experiment" else "Saved memories",
        "artifact": "Experiment artifacts" if scope == "experiment" else "Saved artifacts",
    }.get(record.source, "Saved notes")
    payload = {
        "id": record.id,
        "title": record.title,
        "type": record.type,
        "card": record.card,
        "body": record.body,
        "status": record.status,
        "source": record.source,
        "source_label": source_label,
        "trust": record.trust,
        "kind": "saved_note",
        "memory_role": "saved_context",
        "recall_status": "available",
        "source_tier": "saved",
        "scope": scope,
        "filename": record.path.name,
    }
    payload.update(lineage_payload(record))
    payload.update(artifact_lifecycle_card_fields(record))
    payload.update(scenario_payload(saved_record_scenario_metadata(record)))
    return payload


def serialize_vault_note_card(note: Any) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "type": note.type,
        "card": note.card,
        "body": note.body,
        "source": note.source,
        "source_label": "Reference notes",
        "trust": note.trust,
        "kind": "reference_note",
        "memory_role": "reference_context",
        "recall_status": "available",
        "source_tier": "reference",
        "path": note.relative_path,
        "folder": note.folder,
        "tags": note.tags,
        "modified_at": note.modified_at,
    }


def memory_payload(saved_notes: list[dict[str, Any]], reference_notes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "saved_notes": saved_notes,
        "reference_notes": reference_notes,
        "counts": {
            "saved_notes": len(saved_notes),
            "reference_notes": len(reference_notes),
            "total": len(saved_notes) + len(reference_notes),
        },
    }


def scenario_payload(metadata: dict[str, Any] | None) -> dict[str, Any]:
    cleaned_metadata = _clean_scenario_metadata(metadata)
    return {
        "scenario_kind": cleaned_metadata.get("scenario_kind") if cleaned_metadata else None,
        "scenario": cleaned_metadata,
    }


def saved_record_scenario_metadata(record: Any) -> dict[str, Any] | None:
    if getattr(record, "source", None) != "artifact" and getattr(record, "type", None) != "scenario_comparison":
        return None
    return ArtifactStore.parse_scenario_metadata(record)


def _clean_scenario_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_value = _clean_scenario_metadata_value(value)
        if normalized_value in (None, "", [], {}):
            continue
        cleaned[key] = normalized_value
    return cleaned or None


def _clean_scenario_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = _clean_scenario_metadata_value(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned[str(key).strip()] = normalized
        return cleaned
    if isinstance(value, list):
        cleaned_list: list[Any] = []
        for item in value:
            normalized = _clean_scenario_metadata_value(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned_list.append(normalized)
        return cleaned_list
    normalized_value = str(value).strip()
    return normalized_value or None
