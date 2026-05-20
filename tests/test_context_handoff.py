from __future__ import annotations

from vantage_v5.services.attention_role_projection import build_attention_recall_role_projection
from vantage_v5.services.attention_role_projection import build_working_memory_view_payload
from vantage_v5.services.context_handoff import build_attention_recall_context_handoff


def _payload_has_key(value: object, forbidden_key: str) -> bool:
    if isinstance(value, dict):
        return any(key == forbidden_key or _payload_has_key(item, forbidden_key) for key, item in value.items())
    if isinstance(value, list):
        return any(_payload_has_key(item, forbidden_key) for item in value)
    return False


def test_context_handoff_groups_attention_recall_protocol_visible_and_pinned_roles() -> None:
    long_body = " ".join(["graph traversal details"] * 80)
    request_payload = {
        "message": "Show me the saved Midterm Study Plan",
        "pinned_context_id": "memory:pinned-project-note",
    }
    response_payload = {
        "mode": "chat",
        "selected_attention_resources": [
            {
                "id": "selected-midterm",
                "resource_id": "artifact:midterm-study-plan",
                "kind": "artifact",
                "title": "Midterm Study Plan",
                "source": "artifact",
                "summary": "Study plan for graph priorities.",
                "content": long_body,
            }
        ],
        "visible_artifacts": [
            {
                "id": "midterm-study-plan",
                "kind": "whiteboard",
                "title": "Midterm Study Plan",
                "source": "visible_artifact",
                "summary": "Visible study plan.",
                "content": long_body,
            }
        ],
        "recall": [
            {
                "id": "concept:bfs",
                "kind": "concept",
                "source": "concept",
                "title": "Breadth-First Search",
                "card": "BFS explores graph layers.",
                "body": long_body,
            },
            {
                "id": "email-drafting-protocol",
                "kind": "protocol",
                "source": "protocol",
                "title": "Email Drafting Protocol",
                "card": "Keep emails concise.",
                "body": long_body,
            },
        ],
        "pinned_context": {
            "id": "memory:pinned-project-note",
            "kind": "memory",
            "source": "memory",
            "title": "Pinned Project Note",
            "body": long_body,
        },
        "navigator_selection": {
            "surface_to_open": "whiteboard",
            "primary_resource_id": "artifact:midterm-study-plan",
        },
        "surface_invocation": {
            "primary_surface": "whiteboard",
            "write_behavior": "open_only",
        },
    }

    handoff = build_attention_recall_context_handoff(
        request_payload=request_payload,
        response_payload=response_payload,
    )
    trace_payload = handoff.to_trace_payload()

    assert trace_payload["schema"] == "attention_recall_context_handoff.v1"
    assert trace_payload["roles"]["answer_context"]
    assert trace_payload["roles"]["recall_context"]
    assert trace_payload["roles"]["protocol_guidance"][0]["resource_id"] == "email-drafting-protocol"
    assert trace_payload["roles"]["surface_to_open"][0]["resource_id"] == "artifact:midterm-study-plan"
    assert trace_payload["roles"]["pinned_or_continuity_context"][0]["resource_id"] == "memory:pinned-project-note"
    assert trace_payload["comparison"]["selected_attention_resource_ids"] == ["artifact:midterm-study-plan"]
    assert trace_payload["comparison"]["recall_resource_ids"] == ["concept:bfs", "email-drafting-protocol"]
    assert trace_payload["comparison"]["selected_attention_not_in_recall_ids"] == ["artifact:midterm-study-plan"]
    assert trace_payload["comparison"]["recall_not_in_selected_attention_ids"] == ["concept:bfs", "email-drafting-protocol"]
    assert not _payload_has_key(trace_payload, "content")
    assert not _payload_has_key(trace_payload, "body")
    assert not _payload_has_key(trace_payload, "raw_prompt")
    assert all(len(resource.get("excerpt") or "") <= 320 for resource in trace_payload["resources"])


def test_role_projection_and_working_memory_view_are_built_from_context_handoff() -> None:
    request_payload = {"message": "What is BFS?"}
    response_payload = {
        "mode": "chat",
        "recall": [
            {
                "id": "concept:bfs",
                "kind": "concept",
                "source": "concept",
                "title": "Breadth-First Search",
                "card": "BFS explores graph layers.",
                "body": "BFS visits nodes by distance from the start node.",
            }
        ],
        "workspace_update": None,
        "graph_action": None,
        "created_record": None,
        "artifact_actions": [],
    }

    handoff = build_attention_recall_context_handoff(
        request_payload=request_payload,
        response_payload=response_payload,
    )
    projection = build_attention_recall_role_projection(
        request_payload=request_payload,
        response_payload=response_payload,
    )
    view = build_working_memory_view_payload(
        request_payload=request_payload,
        response_payload=response_payload,
        context_handoff=handoff,
        turn_plan={"version": "test", "write_ledger": {"categories": ["none"]}},
    )

    assert projection == handoff.to_role_projection_payload()
    assert view["schema"] == "working_memory_view.v1"
    assert view["roles"]["recall_context"][0]["resource_id"] == "concept:bfs"
    assert view["comparison"]["recall_resource_ids"] == ["concept:bfs"]
    assert view["execution_summary"]["writes"]["categories"] == ["none"]
    assert not _payload_has_key(view, "body")
    assert not _payload_has_key(view, "raw_prompt")
