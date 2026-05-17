from __future__ import annotations

from vantage_v5.services.chat import build_final_response_trace_payload
from vantage_v5.services.turn_plan import TurnPlanBuilder


def _plan(
    *,
    message: str = "Hello?",
    response: dict | None = None,
    request: dict | None = None,
) -> dict:
    request_payload = {
        "message": message,
        "history": [],
        "workspace_id": None,
        "workspace_scope": "excluded",
        "workspace_content_supplied": False,
        "whiteboard_mode": "auto",
        "pinned_context_id": None,
        "memory_intent": "auto",
        "visible_artifacts": [],
        "pending_workspace_update": None,
    }
    if request:
        request_payload.update(request)
    response_payload = {
        "assistant_message": "Done.",
        "mode": "chat",
        "selected_attention_resources": [],
        "navigator_selection": None,
        "surface_invocation": {
            "intent": "chat_only",
            "primary_surface": "chat",
            "write_behavior": "none",
            "reason": "The turn stays in chat.",
            "trigger": "deterministic_policy",
            "resolved_whiteboard_mode": "chat",
        },
        "workspace": {"context_scope": "excluded"},
        "workspace_update": None,
        "graph_action": None,
        "created_record": None,
        "artifact_actions": [],
        "visible_artifacts": [],
        "turn_interpretation": {"resolved_whiteboard_mode": "chat"},
        "semantic_frame": {},
        "semantic_policy": {},
        "memory_trace_record": {"id": "trace-1"},
    }
    if response:
        response_payload.update(response)
    return TurnPlanBuilder().build(
        request_payload=request_payload,
        response_payload=response_payload,
    ).to_dict()


def _warning_codes(plan: dict) -> set[str]:
    return {
        str(warning.get("code"))
        for warning in plan["validation"]["warnings"]
    }


def test_turn_plan_chat_only_qna() -> None:
    plan = _plan(message="Can you answer in chat?")

    assert plan["request"]["message"] == "Can you answer in chat?"
    assert plan["request"]["turn_id"] == "trace-1"
    assert plan["ui_surface_action"]["surface"] == "none"
    assert plan["write_intent"]["kind"] == "none"
    assert plan["write_intent"]["whiteboard_mode"] == "chat"
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is True
    assert plan["compatibility"]["present"]["surface_invocation"] is True
    assert plan["validation"]["warnings"] == []


def test_turn_plan_saved_artifact_open_only() -> None:
    plan = _plan(
        message="Show me the saved Midterm Study Plan",
        response={
            "navigator_selection": {
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "surface_to_open": "whiteboard",
                "reason": "The user asked to show saved material.",
                "confidence": 0.9,
            },
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "title": "Midterm Study Plan",
                    "kind": "artifact",
                    "source": "artifact",
                    "suggested_surface": "whiteboard",
                    "scope": "durable",
                    "durability": "durable",
                    "is_canonical": False,
                    "content": "# Midterm Study Plan\n\nPractice graphs.",
                }
            ],
            "surface_invocation": {
                "intent": "attention_selected_context",
                "primary_surface": "whiteboard",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
                "reason": "Open the selected material.",
                "trigger": "attention_navigator",
                "selection_authority": "attention_navigator",
            },
        },
    )

    assert plan["retrieval"]["primary_resource_id"] == "artifact:midterm-study-plan"
    assert plan["retrieval"]["openable_selected_resource_id"] == "artifact:midterm-study-plan"
    assert plan["retrieval"]["selected_resources"][0]["content_present"] is True
    assert plan["ui_surface_action"]["surface"] == "whiteboard"
    assert plan["ui_surface_action"]["mode"] == "open_only"
    assert plan["ui_surface_action"]["target_resource_id"] == "artifact:midterm-study-plan"
    assert plan["ui_surface_action"]["authority"] == "navigator_selection"
    assert plan["write_intent"]["kind"] == "ui_open_only"
    assert plan["side_effect_policy"]["allow_workspace_update"] is False
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is False
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "open_only_ui_handoff"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_open_only_with_writes_warns() -> None:
    plan = _plan(
        message="Show me the saved Midterm Study Plan",
        response={
            "navigator_selection": {
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "surface_to_open": "whiteboard",
            },
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "kind": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "attention_selected_context",
                "primary_surface": "whiteboard",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "workspace_update": {"type": "draft_whiteboard", "status": "draft_ready"},
            "graph_action": {"action": "create_concept"},
            "created_record": {"id": "concept:study-plan"},
            "artifact_actions": [{"id": "action-1", "artifact_kind": "calendar", "status": "proposed"}],
        },
    )

    assert "open_only_has_write_side_effects" in _warning_codes(plan)


def test_turn_plan_explicit_whiteboard_draft() -> None:
    plan = _plan(
        message="Draft this in the whiteboard",
        response={
            "surface_invocation": {
                "intent": "durable_artifact",
                "primary_surface": "whiteboard",
                "write_behavior": "draft_only",
                "whiteboard_mode": "draft",
                "resolved_whiteboard_mode": "draft",
                "reason": "The user explicitly asked to draft in the whiteboard.",
                "trigger": "deterministic_policy",
            },
            "workspace_update": {
                "type": "draft_whiteboard",
                "status": "draft_ready",
                "summary": "Draft ready.",
            },
            "turn_interpretation": {
                "resolved_whiteboard_mode": "draft",
                "explicit_whiteboard_draft_request": True,
            },
        },
    )

    assert plan["ui_surface_action"]["surface"] == "whiteboard"
    assert plan["ui_surface_action"]["mode"] == "draft"
    assert plan["write_intent"]["kind"] == "whiteboard_draft"
    assert plan["write_intent"]["explicit_user_intent"] is True
    assert plan["side_effect_policy"]["allow_workspace_update"] is True
    assert plan["side_effect_policy"]["allow_auto_workspace_iteration_artifact"] is True
    assert plan["side_effect_policy"]["actual"]["workspace_update"] is True
    assert plan["execution"]["chat_whiteboard_mode"] == "draft"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_today_calendar_surface() -> None:
    plan = _plan(
        message="What does my day look like?",
        response={
            "surface_invocation": {
                "intent": "schedule_lookup",
                "primary_surface": "calendar_day",
                "write_behavior": "read_only",
                "reason": "The user asked for today's schedule.",
                "trigger": "deterministic_policy",
                "resolved_whiteboard_mode": "chat",
            },
            "active_surface_id": "today-2026-05-13",
            "surface_payloads": [{"id": "today-2026-05-13", "kind": "today_briefing"}],
        },
    )

    assert plan["ui_surface_action"]["surface"] == "calendar_day"
    assert plan["ui_surface_action"]["mode"] == "read_only"
    assert plan["ui_surface_action"]["target_resource_id"] == "today-2026-05-13"
    assert plan["execution"]["surface_payload_policy"] == "build_operational_payload"
    assert plan["side_effect_policy"]["allow_calendar_task_mutation"] is False
    assert plan["validation"]["warnings"] == []


def test_turn_plan_visible_artifact_qna_no_write_policy() -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    plan = _plan(
        message="Can you summarize this study plan?",
        request={"visible_artifacts": [visible_artifact], "workspace_scope": "visible"},
        response={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
                "reason": "Answer using the current view.",
                "trigger": "deterministic_policy",
            },
            "visible_artifacts": [visible_artifact],
            "workspace": {"context_scope": "visible"},
        },
    )

    assert plan["visible_context"]["incoming_visible_artifact_ids"] == ["artifact:midterm-study-plan"]
    assert plan["visible_context"]["response_visible_artifact_ids"] == ["artifact:midterm-study-plan"]
    assert plan["visible_context"]["workspace_in_model_context"] is True
    assert plan["write_intent"]["kind"] == "none"
    assert plan["side_effect_policy"]["allow_workspace_update"] is False
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is False
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "artifact_qna_chat_first"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_visible_artifact_qna_with_write_warns() -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    plan = _plan(
        message="Can you summarize this study plan?",
        request={"visible_artifacts": [visible_artifact], "workspace_scope": "visible"},
        response={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "visible_artifacts": [visible_artifact],
            "workspace": {"context_scope": "visible"},
            "graph_action": {"action": "create_concept"},
            "created_record": {"id": "concept:study-plan-summary"},
        },
    )

    assert "artifact_qna_has_write_side_effects" in _warning_codes(plan)


def test_turn_plan_visible_artifact_qna_with_explicit_save_does_not_warn() -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    plan = _plan(
        message="Save this as a concept.",
        request={"visible_artifacts": [visible_artifact], "workspace_scope": "visible"},
        response={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "visible_artifacts": [visible_artifact],
            "workspace": {"context_scope": "visible"},
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {"actions": [{"type": "save_whiteboard"}]},
            },
            "semantic_policy": {"semantic_action": "save"},
            "graph_action": {"action": "create_concept"},
            "created_record": {"id": "concept:study-plan-summary"},
        },
    )

    assert "artifact_qna_has_write_side_effects" not in _warning_codes(plan)


def test_turn_plan_preserve_surface_no_write_policy() -> None:
    plan = _plan(
        message="leave the calendar open",
        response={
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {
                    "actions": [{"type": "preserve_surface", "target": "calendar"}],
                },
            },
            "surface_invocation": {
                "intent": "preserve_visible_surface",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
                "reason": "The user asked to keep the current visible surface open.",
                "trigger": "deterministic_policy",
            },
        },
    )

    assert plan["ui_surface_action"]["surface"] == "none"
    assert plan["write_intent"]["kind"] == "none"
    assert plan["side_effect_policy"]["allow_workspace_update"] is False
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is False
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "preserve_visible_surface"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_preserve_surface_reclassification_warns() -> None:
    plan = _plan(
        message="leave the calendar open",
        response={
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {
                    "actions": [{"type": "preserve_surface", "target": "calendar"}],
                },
            },
            "surface_invocation": {
                "intent": "preserve_visible_surface",
                "primary_surface": "calendar_day",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "surface_action": {"type": "close_visible_surface"},
            "active_surface_id": "today-2026-05-13",
            "surface_payloads": [{"id": "today-2026-05-13", "kind": "today_briefing"}],
        },
    )

    assert {
        "preserve_surface_reclassified",
        "preserve_surface_has_surface_action",
    }.issubset(_warning_codes(plan))


def test_turn_plan_close_surface_with_writes_warns() -> None:
    plan = _plan(
        message="close the whiteboard",
        response={
            "surface_action": {"type": "close_visible_surface", "status": "requested"},
            "surface_invocation": {
                "intent": "close_visible_surface",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "workspace_update": {"type": "draft_whiteboard"},
            "artifact_actions": [{"artifact_kind": "calendar", "operation": "delete_event"}],
        },
    )

    assert {
        "close_surface_has_write_side_effects",
        "close_surface_has_deletion_semantics",
    }.issubset(_warning_codes(plan))


def test_turn_plan_selected_context_open_without_authority_warns() -> None:
    plan = _plan(
        message="Can you summarize this study plan?",
        response={
            "navigator_selection": {
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "surface_to_open": None,
            },
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "kind": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "attention_selected_context",
                "primary_surface": "whiteboard",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
        },
    )

    assert "selected_context_without_open_authority" in _warning_codes(plan)


def test_turn_plan_today_surface_payload_mismatch_warns() -> None:
    plan = _plan(
        message="What does my day look like?",
        response={
            "surface_invocation": {
                "intent": "schedule_lookup",
                "primary_surface": "calendar_day",
                "write_behavior": "read_only",
                "resolved_whiteboard_mode": "chat",
            },
            "active_surface_id": "today-2026-05-13",
            "surface_payloads": [{"id": "today-2026-05-14", "kind": "today_briefing"}],
        },
    )

    assert "active_surface_payload_mismatch" in _warning_codes(plan)


def test_turn_plan_calendar_mutation_must_be_proposal_only() -> None:
    plan = _plan(
        message="Move the event.",
        response={
            "surface_invocation": {
                "intent": "calendar_mutation",
                "primary_surface": "calendar_day",
                "write_behavior": "read_only",
                "resolved_whiteboard_mode": "chat",
            },
            "active_surface_id": "today-2026-05-13",
            "surface_payloads": [{"id": "today-2026-05-13", "kind": "today_briefing"}],
            "artifact_actions": [
                {
                    "id": "action-1",
                    "artifact_kind": "calendar",
                    "operation": "move_event",
                    "status": "accepted",
                    "requires_confirmation": False,
                }
            ],
        },
    )

    assert "calendar_task_mutation_not_proposal_only" in _warning_codes(plan)


def test_final_response_trace_payload_includes_turn_plan() -> None:
    final_response = build_final_response_trace_payload(
        request_payload={
            "message": "Look at the saved Midterm Study Plan",
            "history": [],
            "workspace_scope": "excluded",
            "workspace_content_supplied": False,
            "whiteboard_mode": "auto",
            "memory_intent": "auto",
            "visible_artifacts": [],
        },
        response_payload={
            "assistant_message": "I found it.",
            "mode": "chat",
            "navigator_selection": {
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "surface_to_open": "whiteboard",
            },
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "title": "Midterm Study Plan",
                    "kind": "artifact",
                    "source": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "attention_selected_context",
                "primary_surface": "whiteboard",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "workspace_update": None,
            "graph_action": None,
            "created_record": None,
            "artifact_actions": [],
            "visible_artifacts": [],
        },
    )

    plan = final_response["turn_plan"]
    assert plan["request"]["message"] == "Look at the saved Midterm Study Plan"
    assert plan["retrieval"]["primary_resource_id"] == "artifact:midterm-study-plan"
    assert plan["ui_surface_action"]["surface"] == "whiteboard"
    assert plan["write_intent"]["kind"] == "ui_open_only"
    assert plan["validation"]["status"] == "ok"
    assert plan["validation"]["warnings"] == []
