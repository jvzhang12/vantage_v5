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


def _payload_contains(value: object, needle: str) -> bool:
    if isinstance(value, dict):
        return any(_payload_contains(key, needle) or _payload_contains(item, needle) for key, item in value.items())
    if isinstance(value, list):
        return any(_payload_contains(item, needle) for item in value)
    if isinstance(value, str):
        return needle in value
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


def test_memory_trace_resources_are_public_safe_across_handoff_projection_and_view() -> None:
    raw_prompt = "Can you help me plan the confidential graph exam retake?"
    raw_assistant = "Sure, your private retake plan should start with BFS and DFS."
    response_payload = {
        "mode": "chat",
        "recall": [
            {
                "id": "memory_trace:turn-20260520",
                "resource_id": "memory_trace:turn-20260520",
                "kind": "memory_trace",
                "source": "memory_trace",
                "title": raw_prompt,
                "label": raw_prompt,
                "summary": raw_prompt,
                "card": raw_assistant,
                "excerpt": raw_assistant,
                "body": f"USER: {raw_prompt}\nASSISTANT: {raw_assistant}",
                "content": f"{raw_prompt}\n{raw_assistant}",
            }
        ],
        "workspace_update": None,
        "graph_action": None,
        "created_record": None,
        "artifact_actions": [],
    }

    handoff = build_attention_recall_context_handoff(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
    )
    trace_payload = handoff.to_trace_payload()
    projection = build_attention_recall_role_projection(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
    )
    view = build_working_memory_view_payload(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
        context_handoff=handoff,
        turn_plan={"version": "test", "write_ledger": {"categories": ["none"]}},
    )

    for payload in (trace_payload, projection, view):
        assert not _payload_contains(payload, raw_prompt)
        assert not _payload_contains(payload, raw_assistant)
        assert not _payload_has_key(payload, "body")
        assert not _payload_has_key(payload, "content")
    safe_alias = "memory_trace:prior-turn-1"
    memory_trace_resource = next(resource for resource in trace_payload["resources"] if resource["resource_id"] == safe_alias)
    assert memory_trace_resource["id"] == safe_alias
    assert memory_trace_resource["title"] == "Prior turn trace"
    assert memory_trace_resource["label"] == "Prior turn trace"
    assert memory_trace_resource["summary"] == "Prior turn context selected by Recall."
    assert memory_trace_resource["excerpt"] is None
    assert trace_payload["roles"]["recall_context"][0]["resource_id"] == safe_alias
    assert projection["roles"]["recall_context"][0]["resource_id"] == safe_alias
    assert view["roles"]["recall_context"][0]["resource_id"] == safe_alias


def test_memory_trace_prompt_derived_storage_ids_are_aliased_publicly() -> None:
    raw_phrase = "can-you-help-me-plan-the-confidential-graph-exam-retake"
    raw_id = f"memory_trace:turn-20260520-{raw_phrase}"
    raw_record_id = f"turn-20260520-120000-{raw_phrase}"
    raw_prompt = "Can you help me plan the confidential graph exam retake?"
    raw_assistant = "The confidential graph exam retake plan should stay private."
    response_payload = {
        "mode": "chat",
        "memory_trace_record": {
            "id": raw_record_id,
            "source": "memory_trace",
            "turn_mode": "chat",
        },
        "recall": [
            {
                "id": raw_id,
                "resource_id": raw_id,
                "kind": "memory_trace",
                "source": "memory_trace",
                "source_label": raw_prompt,
                "title": raw_prompt,
                "summary": raw_prompt,
                "excerpt": raw_assistant,
                "body": f"USER: {raw_prompt}\nASSISTANT: {raw_assistant}",
            }
        ],
        "workspace_update": None,
        "graph_action": None,
        "created_record": None,
        "artifact_actions": [],
    }

    handoff = build_attention_recall_context_handoff(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
    )
    trace_payload = handoff.to_trace_payload()
    projection = build_attention_recall_role_projection(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
    )
    view = build_working_memory_view_payload(
        request_payload={"message": raw_prompt},
        response_payload=response_payload,
        context_handoff=handoff,
        turn_plan={"version": "test", "write_ledger": {"categories": ["none"]}},
    )

    safe_alias = "memory_trace:prior-turn-1"
    for payload in (trace_payload, projection, view):
        assert _payload_contains(payload, safe_alias)
        assert not _payload_contains(payload, raw_id)
        assert not _payload_contains(payload, raw_record_id)
        assert not _payload_contains(payload, raw_phrase)
        assert not _payload_contains(payload, raw_prompt)
        assert not _payload_contains(payload, raw_assistant)
        assert payload["roles"]["recall_context"][0]["resource_id"] == safe_alias
        assert payload["comparison"]["recall_resource_ids"] == [safe_alias]

    assert view["turn"]["trace_id"] == "current-turn"
    assert trace_payload["resources"][0]["id"] == safe_alias
    assert trace_payload["resources"][0]["resource_id"] == safe_alias
    assert trace_payload["roles"]["answer_context"][0]["resource_id"] == safe_alias


def test_synthetic_surface_open_placeholder_does_not_claim_llm_context() -> None:
    response_payload = {
        "mode": "chat",
        "navigator_selection": {
            "surface_to_open": "whiteboard",
            "primary_resource_id": "artifact:missing-study-plan",
        },
        "surface_invocation": {
            "primary_surface": "whiteboard",
            "write_behavior": "open_only",
        },
    }

    handoff = build_attention_recall_context_handoff(
        request_payload={"message": "Open the missing study plan"},
        response_payload=response_payload,
    )
    trace_payload = handoff.to_trace_payload()
    projection = build_attention_recall_role_projection(
        request_payload={"message": "Open the missing study plan"},
        response_payload=response_payload,
    )
    view = build_working_memory_view_payload(
        request_payload={"message": "Open the missing study plan"},
        response_payload=response_payload,
        context_handoff=handoff,
        turn_plan={"version": "test", "write_ledger": {"categories": ["open_only_no_write"]}},
    )

    assert trace_payload["roles"]["surface_to_open"][0]["resource_id"] == "artifact:missing-study-plan"
    assert trace_payload["roles"]["surface_to_open"][0]["sent_to_response_llm"] is None
    assert projection["roles"]["surface_to_open"][0]["sent_to_response_llm"] is None
    assert view["roles"]["surface_to_open"][0]["sent_to_response_llm"] is None
    placeholder = next(resource for resource in view["resources"] if resource["resource_id"] == "artifact:missing-study-plan")
    assert placeholder.get("sent_to_response_llm") is None
