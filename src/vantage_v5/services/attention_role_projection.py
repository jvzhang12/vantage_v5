from __future__ import annotations

from typing import Any

from vantage_v5.services.context_handoff import EXCERPT_LIMIT
from vantage_v5.services.context_handoff import ROLE_NAMES
from vantage_v5.services.context_handoff import SUMMARY_LIMIT
from vantage_v5.services.context_handoff import AttentionRecallContextHandoff
from vantage_v5.services.context_handoff import build_attention_recall_context_handoff
from vantage_v5.services.public_context_projection import public_turn_id
from vantage_v5.services.public_context_projection import public_turn_trace_id

WORKING_MEMORY_VIEW_VERSION = "working_memory_view.v1"


def build_attention_recall_role_projection(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a trace-only role view over finalized context payloads.

    This intentionally observes the already-finalized response contract. It does
    not alter selection, recall, prompt context, routing, writes, or UI behavior.
    """

    return build_attention_recall_context_handoff(
        request_payload=request_payload,
        response_payload=response_payload,
    ).to_role_projection_payload()


def build_working_memory_view_payload(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    role_projection: dict[str, Any] | None = None,
    turn_plan: dict[str, Any] | None = None,
    context_handoff: AttentionRecallContextHandoff | None = None,
) -> dict[str, Any]:
    """Build the product-safe Working Memory view for the latest response.

    The view is a bounded public contract over already-finalized response
    fields. It reuses the Attention/Recall role projection as its source of
    truth and adds a compact execution summary from TurnPlan-compatible fields.
    It does not include raw prompts, full resource bodies, or hidden reasoning.
    """

    handoff = context_handoff if isinstance(context_handoff, AttentionRecallContextHandoff) else None
    projection = role_projection if isinstance(role_projection, dict) else None
    if projection is None:
        handoff = handoff or build_attention_recall_context_handoff(
            request_payload=request_payload,
            response_payload=response_payload,
        )
        projection = handoff.to_role_projection_payload()
    plan = turn_plan if isinstance(turn_plan, dict) else {}
    resources = [
        _working_memory_resource(resource, response_payload=response_payload)
        for resource in _list_of_dicts(projection.get("resources"))
    ]
    roles = {
        role: [
            _working_memory_role_reference(resource)
            for resource in resources
            if role in resource.get("roles", [])
        ]
        for role in ROLE_NAMES
    }
    trace_record = response_payload.get("memory_trace_record")
    trace_id = public_turn_trace_id(trace_record)
    turn_request = plan.get("request") if isinstance(plan.get("request"), dict) else {}
    turn_id = public_turn_id(request_payload.get("turn_id") or turn_request.get("turn_id"), trace_id=trace_id)
    return {
        "schema": WORKING_MEMORY_VIEW_VERSION,
        "turn": {
            "turn_id": turn_id,
            "trace_id": _clean_optional(trace_id),
            "response_mode": _clean_optional(_response_mode_kind(response_payload.get("response_mode"))),
            "mode": _clean_optional(response_payload.get("mode")),
        },
        "roles": roles,
        "resources": resources,
        "comparison": _compact_projection_comparison(projection.get("comparison")),
        "execution_summary": _working_memory_execution_summary(
            response_payload=response_payload,
            turn_plan=plan,
        ),
        "source": {
            "attention_recall_role_projection_schema": _clean_optional(projection.get("schema")),
            "turn_plan_version": _clean_optional(plan.get("version")),
        },
        "notes": [
            "Shows bounded grounding/context/provenance and execution decisions for the latest response.",
            "Does not include hidden reasoning, chain-of-thought, raw prompts, or full resource bodies.",
        ],
    }


def _working_memory_resource(
    resource: dict[str, Any],
    *,
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    roles = _unique([str(role) for role in resource.get("roles", []) if str(role or "").strip()])
    origins = _unique([str(origin) for origin in resource.get("origins", []) if str(origin or "").strip()])
    resource_id = _clean_optional(resource.get("resource_id")) or _clean_optional(resource.get("id")) or "resource"
    compact = {
        "id": _clean_optional(resource.get("id")) or resource_id,
        "resource_id": resource_id,
        "kind": _clean_optional(resource.get("kind")),
        "type": _clean_optional(resource.get("type")),
        "title": _clean_optional(resource.get("title")),
        "label": _clean_optional(resource.get("label")),
        "roles": roles,
        "origins": origins,
        "flags": _compact_flags(resource.get("flags")),
        "summary": _short_text(resource.get("summary"), limit=SUMMARY_LIMIT),
        "excerpt": _short_text(resource.get("excerpt"), limit=EXCERPT_LIMIT),
        "sent_to_response_llm": resource.get("sent_to_response_llm")
        if isinstance(resource.get("sent_to_response_llm"), bool)
        else None,
        "provenance": _compact_provenance(resource.get("provenance")),
        "influence": {
            "answer_generation": "answer_context" in roles,
            "ui_surface_action": "surface_to_open" in roles,
            "write_or_proposal_decision": _resource_influenced_write_or_proposal(resource_id, response_payload),
        },
    }
    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def _working_memory_role_reference(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": resource.get("resource_id"),
        "kind": resource.get("kind"),
        "title": resource.get("title"),
        "origins": resource.get("origins") or [],
        "sent_to_response_llm": resource.get("sent_to_response_llm"),
    }


def _working_memory_execution_summary(
    *,
    response_payload: dict[str, Any],
    turn_plan: dict[str, Any],
) -> dict[str, Any]:
    ui_surface_action = turn_plan.get("ui_surface_action") if isinstance(turn_plan.get("ui_surface_action"), dict) else {}
    write_ledger = turn_plan.get("write_ledger") if isinstance(turn_plan.get("write_ledger"), dict) else {}
    write_projection = turn_plan.get("write_projection") if isinstance(turn_plan.get("write_projection"), dict) else {}
    graph_action = response_payload.get("graph_action") if isinstance(response_payload.get("graph_action"), dict) else None
    created_record = response_payload.get("created_record") if isinstance(response_payload.get("created_record"), dict) else None
    artifact_actions = _list_of_dicts(response_payload.get("artifact_actions"))
    return {
        "surface": {
            "mode": _clean_optional(ui_surface_action.get("mode")),
            "surface": _clean_optional(ui_surface_action.get("surface")),
            "target_resource_id": _clean_optional(ui_surface_action.get("target_resource_id")),
            "target_resource_kind": _clean_optional(ui_surface_action.get("target_resource_kind")),
            "authority": _clean_optional(ui_surface_action.get("authority")),
            "active_surface_id": _clean_optional(response_payload.get("active_surface_id")),
            "surface_payload_count": len(_list_of_dicts(response_payload.get("surface_payloads"))),
        },
        "writes": {
            "categories": list(write_ledger.get("categories") or ["none"]),
            "intended_write_kind": _clean_optional(write_projection.get("intended_write_kind")),
            "effect_agreement": _clean_optional(write_projection.get("effect_agreement")),
            "workspace_update_type": _workspace_update_type(response_payload.get("workspace_update")),
            "graph_action_type": _clean_optional(graph_action.get("type") if graph_action else None),
            "created_record": _compact_created_record(created_record),
            "artifact_action_count": len(artifact_actions),
            "proposal_count": sum(1 for action in artifact_actions if _is_proposed_artifact_action(action)),
        },
    }


def _compact_flags(value: Any) -> dict[str, bool]:
    flags = value if isinstance(value, dict) else {}
    return {
        "selected": bool(flags.get("selected")),
        "visible": bool(flags.get("visible")),
        "pinned": bool(flags.get("pinned")),
    }


def _compact_provenance(value: Any) -> dict[str, Any]:
    provenance = value if isinstance(value, dict) else {}
    compact: dict[str, Any] = {}
    for key in ("source", "source_label", "scope", "durability", "is_canonical"):
        item = provenance.get(key)
        if item not in (None, "", {}):
            compact[key] = item
    source_status = provenance.get("source_status")
    if isinstance(source_status, dict):
        compact_status = {
            key: source_status.get(key)
            for key in ("store", "read_only", "writable")
            if key in source_status
        }
        if compact_status:
            compact["source_status"] = compact_status
    return compact


def _compact_projection_comparison(value: Any) -> dict[str, list[str]]:
    comparison = value if isinstance(value, dict) else {}
    keys = (
        "selected_attention_resource_ids",
        "visible_resource_ids",
        "pinned_resource_ids",
        "recall_resource_ids",
        "selected_recall_overlap_ids",
        "selected_attention_not_in_recall_ids",
        "recall_not_in_selected_attention_ids",
    )
    return {
        key: _unique([str(item) for item in comparison.get(key, [])])
        if isinstance(comparison.get(key), list)
        else []
        for key in keys
    }


def _resource_influenced_write_or_proposal(resource_id: str, response_payload: dict[str, Any]) -> bool | None:
    target_ids = _write_or_proposal_target_ids(response_payload)
    if not target_ids:
        return None
    return _normalize_resource_id(resource_id) in target_ids


def _write_or_proposal_target_ids(response_payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    graph_action = response_payload.get("graph_action")
    if isinstance(graph_action, dict):
        for key in ("record_id", "concept_id", "artifact_id", "memory_id", "target_id"):
            value = _clean_optional(graph_action.get(key))
            if value:
                ids.add(_normalize_resource_id(value))
    created_record = response_payload.get("created_record")
    if isinstance(created_record, dict):
        for key in ("resource_id", "id", "record_id", "concept_id"):
            value = _clean_optional(created_record.get(key))
            if value:
                ids.add(_normalize_resource_id(value))
    for action in _list_of_dicts(response_payload.get("artifact_actions")):
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        for candidate in (action, payload):
            for key in ("id", "resource_id", "target_id", "artifact_id", "task_id", "event_id"):
                value = _clean_optional(candidate.get(key))
                if value:
                    ids.add(_normalize_resource_id(value))
    return ids


def _workspace_update_type(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return _clean_optional(value.get("type") or value.get("status") or value.get("proposal_kind"))


def _compact_created_record(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    compact = {
        "id": _clean_optional(value.get("id") or value.get("record_id") or value.get("concept_id")),
        "kind": _clean_optional(value.get("kind") or value.get("type")),
        "type": _clean_optional(value.get("type")),
        "title": _clean_optional(value.get("title")),
    }
    return {key: item for key, item in compact.items() if item not in (None, "", {}, [])}


def _is_proposed_artifact_action(action: dict[str, Any]) -> bool:
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    return str(action.get("status") or payload.get("status") or "").strip().lower() == "proposed"


def _response_mode_kind(value: Any) -> str | None:
    if isinstance(value, dict):
        return _clean_optional(value.get("kind") or value.get("mode"))
    return _clean_optional(value)


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _short_text(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clean_optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _normalize_resource_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("candidate-"):
        return text.removeprefix("candidate-")
    return text
