from __future__ import annotations

from typing import Any


def build_write_review(
    record: dict[str, Any],
    *,
    write_reason: str | None = None,
    scope: str | None = None,
    durability: str | None = None,
) -> dict[str, Any]:
    """Build the read-only review DTO for records written by the current turn."""

    record_scope = _clean(scope) or _clean(record.get("scope")) or "durable"
    record_durability = _clean(durability) or _clean(record.get("durability")) or (
        "temporary" if record_scope == "experiment" else "durable"
    )
    reason = _clean(write_reason) or _clean(record.get("why_learned")) or "Saved so this record can be reviewed later."
    record_source = _clean(record.get("source")) or "unknown"
    record_kind = _clean(record.get("kind")) or _kind_for(record_source, _clean(record.get("type")))

    return {
        "write_reason": reason,
        "scope": record_scope,
        "durability": record_durability,
        "record": {
            "id": _clean(record.get("id")),
            "title": _clean(record.get("title")),
            "source": record_source,
            "kind": record_kind,
            "type": _clean(record.get("type")),
        },
        "allowed_actions": [
            {
                "kind": "open_in_whiteboard",
                "label": "Open in whiteboard",
                "primary": True,
            },
            {
                "kind": "revise_in_whiteboard",
                "label": "Revise in whiteboard",
                "primary": True,
            },
            {
                "kind": "pin_for_next_turn",
                "label": "Pin for next turn",
                "primary": True,
            },
        ],
        "unsupported_actions": [
            {
                "kind": "direct_mutation",
                "label": "Direct mutation is not supported",
            }
        ],
        "direct_mutation_supported": False,
        "mutation_supported": False,
    }


def ensure_write_review(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record.get("write_review"), dict):
        record["write_review"] = build_write_review(record)
    return record


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _kind_for(source: str, record_type: str | None) -> str:
    if source == "concept":
        return "protocol" if record_type == "protocol" else "concept"
    if source in {"memory", "artifact"}:
        return "saved_note"
    if source == "memory_trace":
        return "memory_trace"
    if source == "workspace":
        return "workspace_branch"
    return "record"
