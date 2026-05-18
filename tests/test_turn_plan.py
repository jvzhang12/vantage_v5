from __future__ import annotations

import pytest

from vantage_v5.services.chat import build_final_response_trace_payload
from vantage_v5.services.turn_plan import project_write_intent_compatibility
from vantage_v5.services.turn_plan import TurnPlanBuilder
from vantage_v5.services.turn_plan import build_turn_plan_artifact_write_authority
from vantage_v5.services.turn_plan import build_turn_plan_memory_write_authority
from vantage_v5.services.turn_plan import build_turn_plan_surface_authority


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
    assert plan["write_ledger"]["categories"] == ["none"]
    assert plan["write_ledger"]["has_write_side_effects"] is False
    assert plan["write_ledger"]["no_write_reason"] == "no_write_effects"
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
    assert plan["write_ledger"]["categories"] == ["open_only_no_write"]
    assert plan["write_ledger"]["actual_write_effect_count"] == 0
    assert plan["write_ledger"]["no_write_reason"] == "open_only_ui_handoff"
    assert plan["side_effect_policy"]["allow_workspace_update"] is False
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is False
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "open_only_ui_handoff"
    assert plan["execution"]["suppress_auto_graph_writes"] is True
    assert plan["execution"]["artifact_action_policy"] == "disabled"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_surface_authority_open_only_blocks_writes_and_payloads() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
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
        }
    )

    assert authority.is_whiteboard_open_only is True
    assert authority.is_close is False
    assert authority.is_preserve is False
    assert authority.suppress_auto_graph_writes is True
    assert authority.blocks_artifact_actions is True
    assert authority.writes_forbidden is True
    assert authority.no_write_reason == "open_only_ui_handoff"
    assert authority.enforced_no_write_categories == ("open_only_no_write",)
    assert authority.blocks_protocol_writes is True
    assert authority.surface_payload_policy == "none"
    assert authority.ui_surface_action.target_resource_id == "artifact:midterm-study-plan"


def test_turn_plan_selected_artifact_context_without_open_has_no_warning() -> None:
    plan = _plan(
        message="Can you use the saved material as context?",
        response={
            "navigator_selection": {
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "surface_to_open": None,
            },
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "title": "Midterm Study Plan",
                    "kind": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "chat_only",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
        },
    )

    assert plan["retrieval"]["selected_resource_ids"] == ["artifact:midterm-study-plan"]
    assert plan["ui_surface_action"]["surface"] == "none"
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

    assert "open_only_with_write_side_effect" in _warning_codes(plan)


def test_turn_plan_open_only_requires_selected_openable_target() -> None:
    plan = _plan(
        message="Show me the saved study plan.",
        response={
            "navigator_selection": {
                "selected_ids": ["concept:study-plan"],
                "primary_resource_id": "concept:study-plan",
                "surface_to_open": "whiteboard",
            },
            "selected_attention_resources": [
                {
                    "resource_id": "concept:study-plan",
                    "kind": "concept",
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

    assert "saved_artifact_open_target_not_selected" in _warning_codes(plan)


def test_turn_plan_open_target_conflict_warns() -> None:
    plan = _plan(
        message="Open the saved Midterm Study Plan.",
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
                "target_resource_id": "artifact:other-plan",
                "write_behavior": "open_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
        },
    )

    assert "ui_open_target_conflicts_with_selected_primary" in _warning_codes(plan)


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
    assert plan["write_ledger"]["categories"] == ["pending_whiteboard_draft"]
    assert plan["write_ledger"]["entries"][0]["field_paths"] == ["workspace_update"]
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
    assert plan["write_ledger"]["categories"] == ["none"]
    assert plan["write_ledger"]["no_write_reason"] == "artifact_qna_chat_first"
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

    assert "visible_artifact_qna_with_durable_write" in _warning_codes(plan)


def test_turn_plan_selected_artifact_qna_with_durable_write_warns() -> None:
    plan = _plan(
        message="Can you summarize this study plan?",
        response={
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "kind": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "chat_only",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "graph_action": {"action": "create_concept"},
            "created_record": {"id": "concept:study-plan-summary"},
        },
    )

    assert "visible_artifact_qna_with_durable_write" in _warning_codes(plan)


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

    assert "visible_artifact_qna_with_durable_write" not in _warning_codes(plan)
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is True
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None


@pytest.mark.parametrize("action_type", ["artifact_save", "artifact_publish"])
def test_turn_plan_visible_artifact_qna_with_real_semantic_write_action_does_not_suppress(
    action_type: str,
) -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    graph_action_type = (
        "save_workspace_iteration_artifact"
        if action_type == "artifact_save"
        else "promote_workspace_to_artifact"
    )
    plan = _plan(
        message="Save this whiteboard.",
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
            "semantic_policy": {"action_type": action_type, "semantic_action": action_type},
            "graph_action": {"type": graph_action_type},
            "created_record": {"id": "midterm-study-plan-snapshot", "source": "artifact"},
        },
    )

    assert plan["side_effect_policy"]["allow_auto_graph_write"] is True
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None
    assert plan["write_ledger"]["categories"] == ["artifact_save_or_promotion"]
    assert plan["write_projection"]["intended_write_kind"] == action_type
    assert plan["write_projection"]["authority"] == "semantic_policy"
    assert plan["write_projection"]["actual_write_categories"] == ["artifact_save_or_promotion"]
    assert plan["write_projection"]["effect_agreement"] == "aligned"
    assert "visible_artifact_qna_with_durable_write" not in _warning_codes(plan)


@pytest.mark.parametrize(
    ("action_type", "graph_action_type", "expected_kind"),
    [
        ("artifact_save", "save_workspace_iteration_artifact", "artifact_save"),
        ("artifact_publish", "promote_workspace_to_artifact", "artifact_publish"),
    ],
)
def test_turn_plan_write_projection_enriches_surface_invocation_for_semantic_artifact_writes(
    action_type: str,
    graph_action_type: str,
    expected_kind: str,
) -> None:
    response = {
        "surface_invocation": {
            "intent": "general_chat",
            "primary_surface": "chat",
            "write_behavior": "none",
            "whiteboard_mode": "chat",
            "resolved_whiteboard_mode": "chat",
        },
        "semantic_policy": {"action_type": action_type, "semantic_action": action_type},
        "graph_action": {"type": graph_action_type},
        "created_record": {"id": "midterm-study-plan-snapshot", "source": "artifact"},
    }

    projected = project_write_intent_compatibility(
        request_payload={"message": "Save this whiteboard.", "memory_intent": "auto"},
        response_payload=response,
    )

    invocation = projected["surface_invocation"]
    assert invocation["intent"] == expected_kind
    assert invocation["legacy_intent"] == "general_chat"
    assert invocation["write_behavior"] == "committed_write"
    assert invocation["legacy_write_behavior"] == "none"
    assert invocation["write_intent"]["kind"] == expected_kind
    assert invocation["write_intent"]["authority"] == "semantic_policy"
    assert invocation["write_intent"]["effect_agreement"] == "aligned"
    assert invocation["write_effects"][0]["category"] == "artifact_save_or_promotion"

    plan = TurnPlanBuilder().build(
        request_payload={"message": "Save this whiteboard.", "memory_intent": "auto"},
        response_payload=projected,
    ).to_dict()
    assert plan["write_projection"]["intended_write_kind"] == expected_kind
    assert plan["write_projection"]["compatibility_projection"]["surface_invocation_has_write_intent"] is True
    assert plan["artifact_write_authority"]["action"] == expected_kind
    assert plan["artifact_write_authority"]["allowed"] is True
    assert plan["artifact_write_authority"]["denied_reason"] is None
    assert plan["validation"]["warnings"] == []


@pytest.mark.parametrize("action_type", ["artifact_save", "artifact_publish"])
def test_turn_plan_artifact_write_authority_allows_structured_save_publish(
    action_type: str,
) -> None:
    authority = build_turn_plan_artifact_write_authority(
        request_payload={
            "message": "Save this whiteboard.",
            "workspace_scope": "visible",
            "workspace_has_content": True,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "semantic_policy": {
                "action_type": action_type,
                "semantic_action": action_type,
                "should_clarify": False,
            },
        },
    )

    assert authority.action == action_type
    assert authority.allowed is True
    assert authority.denied_reason is None
    assert authority.authority == "semantic_policy"
    assert authority.target_available is True
    assert authority.requires_clarification is False


@pytest.mark.parametrize(
    ("response_payload", "expected_reason"),
    [
        (
            {
                "surface_invocation": {
                    "intent": "attention_selected_context",
                    "primary_surface": "whiteboard",
                    "write_behavior": "open_only",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
                "navigator_selection": {
                    "primary_resource_id": "artifact:midterm-study-plan",
                    "surface_to_open": "whiteboard",
                },
                "selected_attention_resources": [
                    {"resource_id": "artifact:midterm-study-plan", "kind": "artifact"}
                ],
                "semantic_policy": {
                    "action_type": "artifact_save",
                    "semantic_action": "artifact_save",
                    "should_clarify": False,
                },
            },
            "open_only_ui_handoff",
        ),
        (
            {
                "surface_invocation": {
                    "intent": "preserve_visible_surface",
                    "primary_surface": "chat",
                    "write_behavior": "none",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
                "turn_interpretation": {
                    "control_panel": {"actions": [{"type": "preserve_surface", "target": "whiteboard"}]},
                },
                "semantic_policy": {
                    "action_type": "artifact_publish",
                    "semantic_action": "artifact_publish",
                    "should_clarify": False,
                },
            },
            "preserve_visible_surface",
        ),
        (
            {
                "surface_action": {"type": "close_visible_surface", "target": "whiteboard"},
                "surface_invocation": {
                    "intent": "close_visible_surface",
                    "primary_surface": "chat",
                    "write_behavior": "none",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
                "semantic_policy": {
                    "action_type": "artifact_save",
                    "semantic_action": "artifact_save",
                    "should_clarify": False,
                },
            },
            "close_visible_surface",
        ),
    ],
)
def test_turn_plan_artifact_write_authority_hard_no_write_wins(
    response_payload: dict,
    expected_reason: str,
) -> None:
    authority = build_turn_plan_artifact_write_authority(
        request_payload={
            "message": "Save this whiteboard.",
            "workspace_scope": "visible",
            "workspace_has_content": True,
        },
        response_payload=response_payload,
    )

    assert authority.action in {"artifact_save", "artifact_publish"}
    assert authority.allowed is False
    assert authority.blocks_candidate_write is True
    assert authority.denied_reason == expected_reason


def test_turn_plan_artifact_write_authority_denies_missing_target() -> None:
    authority = build_turn_plan_artifact_write_authority(
        request_payload={
            "message": "Save this.",
            "workspace_scope": "excluded",
            "workspace_has_content": False,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "semantic_policy": {
                "action_type": "artifact_save",
                "semantic_action": "artifact_save",
                "should_clarify": False,
            },
        },
    )

    assert authority.action == "artifact_save"
    assert authority.allowed is False
    assert authority.denied_reason == "artifact_write_target_unavailable_or_ambiguous"
    assert authority.target_available is False


def test_turn_plan_artifact_write_authority_recognizes_control_panel_save() -> None:
    authority = build_turn_plan_artifact_write_authority(
        request_payload={
            "message": "Save this whiteboard.",
            "workspace_scope": "visible",
            "workspace_has_content": True,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "turn_interpretation": {
                "control_panel": {"actions": [{"type": "save_whiteboard"}]},
            },
        },
    )

    assert authority.action == "artifact_save"
    assert authority.allowed is True
    assert authority.authority == "control_panel"
    assert authority.source_field_paths == ("turn_interpretation.control_panel.actions[0].type",)


def test_turn_plan_visible_artifact_qna_with_memory_intent_remember_does_not_suppress() -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    plan = _plan(
        message="Remember this study plan summary.",
        request={
            "visible_artifacts": [visible_artifact],
            "workspace_scope": "visible",
            "memory_intent": "remember",
        },
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
        },
    )

    assert plan["side_effect_policy"]["allow_auto_graph_write"] is True
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None
    assert plan["execution"]["suppress_auto_graph_writes"] is False
    assert plan["validation"]["warnings"] == []


def test_turn_plan_surface_authority_visible_artifact_qna_forbids_writes() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "visible_artifacts": [
                {
                    "id": "artifact:midterm-study-plan",
                    "kind": "whiteboard",
                    "title": "Midterm Study Plan",
                }
            ],
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {"actions": [{"type": "respond"}]},
            },
        }
    )

    assert authority.writes_forbidden is True
    assert authority.suppress_auto_graph_writes is True
    assert authority.blocks_artifact_actions is True
    assert authority.blocks_protocol_writes is False
    assert authority.no_write_reason == "artifact_qna_chat_first"
    assert authority.enforced_no_write_categories == ("visible_selected_artifact_qna",)
    assert authority.ui_surface_action.mode == "none"


def test_turn_plan_surface_authority_selected_artifact_qna_forbids_writes() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "selected_attention_resources": [
                {
                    "resource_id": "artifact:midterm-study-plan",
                    "kind": "artifact",
                    "suggested_surface": "whiteboard",
                }
            ],
            "surface_invocation": {
                "intent": "selected_material_question",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {"actions": [{"type": "respond"}]},
            },
        }
    )

    assert authority.writes_forbidden is True
    assert authority.suppress_auto_graph_writes is True
    assert authority.blocks_artifact_actions is True
    assert authority.blocks_protocol_writes is False
    assert authority.no_write_reason == "artifact_qna_chat_first"
    assert authority.enforced_no_write_categories == ("visible_selected_artifact_qna",)


def test_turn_plan_surface_authority_selected_non_artifact_question_allows_meta_path() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "selected_attention_resources": [
                {
                    "resource_id": "visible:calendar-week-2026-05-11",
                    "kind": "calendar_week",
                    "suggested_surface": "calendar_week",
                }
            ],
            "surface_invocation": {
                "intent": "selected_material_question",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {"actions": [{"type": "respond"}]},
            },
        }
    )

    assert authority.writes_forbidden is False
    assert authority.suppress_auto_graph_writes is False
    assert authority.blocks_artifact_actions is False
    assert authority.no_write_reason is None


def test_turn_plan_surface_authority_artifact_qna_explicit_save_allows_existing_write_paths() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "visible_artifacts": [
                {
                    "id": "artifact:midterm-study-plan",
                    "kind": "whiteboard",
                    "title": "Midterm Study Plan",
                }
            ],
            "turn_interpretation": {
                "resolved_whiteboard_mode": "chat",
                "control_panel": {"actions": [{"type": "save_whiteboard"}]},
            },
            "semantic_policy": {"semantic_action": "save"},
        }
    )

    assert authority.writes_forbidden is False
    assert authority.suppress_auto_graph_writes is False
    assert authority.blocks_artifact_actions is False
    assert authority.no_write_reason is None
    assert authority.enforced_no_write_categories == ()


def test_turn_plan_surface_authority_artifact_qna_memory_intent_allows_existing_write_paths() -> None:
    authority = build_turn_plan_surface_authority(
        request_payload={"memory_intent": "remember"},
        response_payload={
            "surface_invocation": {
                "intent": "current_artifact_followup",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "visible_artifacts": [
                {
                    "id": "artifact:midterm-study-plan",
                    "kind": "whiteboard",
                    "title": "Midterm Study Plan",
                }
            ],
        },
    )

    assert authority.writes_forbidden is False
    assert authority.suppress_auto_graph_writes is False
    assert authority.blocks_artifact_actions is False
    assert authority.blocks_protocol_writes is False
    assert authority.no_write_reason is None


def test_turn_plan_write_projection_records_memory_intent_authority() -> None:
    plan = _plan(
        message="Remember that I prefer morning study blocks.",
        request={"memory_intent": "remember"},
        response={
            "graph_action": {"type": "create_memory", "record_id": "memory:morning-study"},
            "created_record": {"id": "memory:morning-study", "source": "memory"},
        },
    )

    assert plan["write_projection"]["intended_write_kind"] == "memory_write"
    assert plan["write_projection"]["authority"] == "memory_intent"
    assert plan["write_projection"]["effect_agreement"] == "aligned"
    assert plan["memory_write_authority"]["action"] == "memory_write"
    assert plan["memory_write_authority"]["allowed"] is True
    assert plan["memory_write_authority"]["authority"] == "memory_intent"
    assert "write_effect_without_projected_intent" not in _warning_codes(plan)


def test_turn_plan_memory_write_authority_allows_memory_intent() -> None:
    authority = build_turn_plan_memory_write_authority(
        request_payload={
            "message": "Remember that I prefer morning study blocks.",
            "assistant_message": "Got it.",
            "memory_intent": "remember",
            "memory_write_content_available": True,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
        },
    )

    assert authority.action == "memory_write"
    assert authority.allowed is True
    assert authority.denied_reason is None
    assert authority.authority == "memory_intent"
    assert authority.source_field_paths == ("request.memory_intent",)


def test_turn_plan_memory_write_authority_allows_control_panel_remember() -> None:
    authority = build_turn_plan_memory_write_authority(
        request_payload={
            "message": "Remember this.",
            "assistant_message": "Got it.",
            "memory_intent": "auto",
            "memory_write_content_available": True,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "turn_interpretation": {"control_panel": {"actions": [{"type": "remember"}]}},
        },
    )

    assert authority.action == "memory_write"
    assert authority.allowed is True
    assert authority.authority == "control_panel"
    assert authority.source_field_paths == ("turn_interpretation.control_panel.actions[0].type",)


@pytest.mark.parametrize(
    ("response_payload", "expected_reason"),
    [
        (
            {
                "surface_invocation": {
                    "intent": "attention_selected_context",
                    "primary_surface": "whiteboard",
                    "write_behavior": "open_only",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
                "navigator_selection": {
                    "primary_resource_id": "artifact:midterm-study-plan",
                    "surface_to_open": "whiteboard",
                },
                "selected_attention_resources": [
                    {"resource_id": "artifact:midterm-study-plan", "kind": "artifact"}
                ],
            },
            "open_only_ui_handoff",
        ),
        (
            {
                "surface_invocation": {
                    "intent": "preserve_visible_surface",
                    "primary_surface": "chat",
                    "write_behavior": "none",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
                "turn_interpretation": {
                    "control_panel": {"actions": [{"type": "preserve_surface", "target": "whiteboard"}]},
                },
            },
            "preserve_visible_surface",
        ),
        (
            {
                "surface_action": {"type": "close_visible_surface", "target": "whiteboard"},
                "surface_invocation": {
                    "intent": "close_visible_surface",
                    "primary_surface": "chat",
                    "write_behavior": "none",
                    "whiteboard_mode": "chat",
                    "resolved_whiteboard_mode": "chat",
                },
            },
            "close_visible_surface",
        ),
    ],
)
def test_turn_plan_memory_write_authority_hard_no_write_wins(
    response_payload: dict,
    expected_reason: str,
) -> None:
    authority = build_turn_plan_memory_write_authority(
        request_payload={
            "message": "Remember this.",
            "assistant_message": "Got it.",
            "memory_intent": "remember",
            "memory_write_content_available": True,
        },
        response_payload=response_payload,
    )

    assert authority.action == "memory_write"
    assert authority.allowed is False
    assert authority.blocks_candidate_write is True
    assert authority.denied_reason == expected_reason


def test_turn_plan_memory_write_authority_denies_missing_content() -> None:
    authority = build_turn_plan_memory_write_authority(
        request_payload={
            "message": "",
            "assistant_message": "",
            "workspace_content": "",
            "memory_intent": "remember",
            "memory_write_content_available": False,
        },
        response_payload={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
        },
    )

    assert authority.action == "memory_write"
    assert authority.allowed is False
    assert authority.denied_reason == "memory_write_content_unavailable_or_unsafe"


def test_turn_plan_memory_write_effect_without_authority_warns() -> None:
    plan = _plan(
        message="Remember this.",
        response={
            "graph_action": {"type": "create_memory", "record_id": "memory:raw-remember"},
            "created_record": {"id": "memory:raw-remember", "source": "memory"},
        },
    )

    assert plan["memory_write_authority"]["action"] == "memory_write"
    assert plan["memory_write_authority"]["allowed"] is False
    assert plan["memory_write_authority"]["denied_reason"] == "missing_structured_memory_write_intent"
    assert "memory_write_effect_without_authority" in _warning_codes(plan)
    assert "write_effect_without_projected_intent" not in _warning_codes(plan)
    assert "compatibility_no_write_with_write_effect" in _warning_codes(plan)


def test_turn_plan_protocol_write_authority_lifts_artifact_qna_no_write() -> None:
    visible_artifact = {
        "id": "artifact:midterm-study-plan",
        "kind": "whiteboard",
        "title": "Midterm Study Plan",
    }
    plan = _plan(
        message="For emails, always sign with Jordan Zhang; summarize this study plan.",
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
            "graph_action": {"type": "upsert_protocol", "record_id": "email-drafting-protocol"},
            "created_record": {"id": "email-drafting-protocol", "type": "protocol"},
        },
    )

    assert plan["side_effect_policy"]["allow_auto_graph_write"] is True
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] is None
    assert plan["write_ledger"]["categories"] == ["concept_write"]
    assert plan["write_projection"]["intended_write_kind"] == "protocol_write"
    assert plan["write_projection"]["authority"] == "protocol_interpreter"
    assert "visible_artifact_qna_with_durable_write" not in _warning_codes(plan)


def test_turn_plan_warns_when_write_effect_has_only_legacy_no_write_compatibility() -> None:
    plan = _plan(
        message="Summarize this study plan.",
        response={
            "surface_invocation": {
                "intent": "general_chat",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "graph_action": {"action": "create_concept"},
            "created_record": {"id": "concept:study-plan-summary", "type": "concept"},
        },
    )

    assert plan["write_projection"]["authority"] == "existing_write_effect"
    assert plan["write_projection"]["effect_agreement"] == "effect_without_explicit_intent"
    assert "compatibility_no_write_with_write_effect" in _warning_codes(plan)


def test_turn_plan_write_ledger_pending_offer() -> None:
    plan = _plan(
        message="Can you draft an email?",
        response={
            "surface_invocation": {
                "intent": "durable_artifact",
                "primary_surface": "whiteboard",
                "write_behavior": "none",
                "whiteboard_mode": "offer",
                "resolved_whiteboard_mode": "offer",
            },
            "workspace_update": {
                "type": "whiteboard_offer",
                "status": "offered",
                "summary": "Offer a whiteboard draft.",
            },
        },
    )

    assert plan["write_ledger"]["categories"] == ["pending_whiteboard_offer"]
    assert plan["write_ledger"]["entries"][0]["status"] == "offered"
    assert plan["write_ledger"]["proposed_write_count"] == 1


def test_turn_plan_write_ledger_workspace_update_snapshot() -> None:
    plan = _plan(
        message="Save this workspace snapshot.",
        response={
            "workspace_update": {
                "type": "save_snapshot",
                "status": "saved",
                "workspace_id": "draft-1",
            },
        },
    )

    assert plan["write_ledger"]["categories"] == ["draft_snapshot_workspace_update"]
    assert plan["write_ledger"]["entries"][0]["committed"] is True
    assert plan["write_ledger"]["entries"][0]["target_id"] == "draft-1"


def test_turn_plan_write_ledger_artifact_save_or_promotion() -> None:
    plan = _plan(
        message="Publish this artifact.",
        response={
            "graph_action": {"type": "promote_workspace_to_artifact", "record_id": "midterm-study-plan"},
            "created_record": {
                "id": "midterm-study-plan",
                "source": "artifact",
                "artifact_lifecycle": "promoted_artifact",
            },
        },
    )

    assert plan["write_ledger"]["categories"] == ["artifact_save_or_promotion"]
    assert plan["write_ledger"]["entries"][0]["field_paths"] == ["graph_action", "created_record"]
    assert plan["write_ledger"]["committed_write_count"] == 1


def test_turn_plan_write_ledger_concept_write() -> None:
    plan = _plan(
        message="Remember this as a concept.",
        response={
            "graph_action": {"action": "create_concept", "concept_id": "concept:study-cycle"},
            "created_record": {"id": "concept:study-cycle", "type": "concept"},
        },
    )

    assert plan["write_ledger"]["categories"] == ["concept_write"]
    assert plan["write_ledger"]["entries"][0]["target_kind"] == "concept"


def test_turn_plan_write_ledger_memory_write() -> None:
    plan = _plan(
        message="Remember that I prefer morning study blocks.",
        response={
            "graph_action": {"type": "create_memory", "record_id": "memory:morning-study"},
            "created_record": {"id": "memory:morning-study", "source": "memory"},
        },
    )

    assert plan["write_ledger"]["categories"] == ["memory_write"]
    assert plan["write_ledger"]["entries"][0]["target_kind"] == "memory"


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
    assert plan["ui_surface_action"]["mode"] == "preserve"
    assert plan["write_intent"]["kind"] == "none"
    assert plan["write_ledger"]["categories"] == ["none"]
    assert plan["write_ledger"]["no_write_reason"] == "preserve_visible_surface"
    assert plan["side_effect_policy"]["allow_workspace_update"] is False
    assert plan["side_effect_policy"]["allow_auto_graph_write"] is False
    assert plan["side_effect_policy"]["allow_artifact_actions"] is False
    assert plan["side_effect_policy"]["suppress_auto_graph_writes_reason"] == "preserve_visible_surface"
    assert plan["validation"]["warnings"] == []


def test_turn_plan_surface_authority_preserve_short_circuits_surface_payloads() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "turn_interpretation": {
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
                "reason": "The user asked to keep the visible surface open.",
            },
        }
    )

    assert authority.is_preserve is True
    assert authority.is_close is False
    assert authority.suppress_auto_graph_writes is True
    assert authority.blocks_artifact_actions is True
    assert authority.blocks_protocol_writes is True
    assert authority.writes_forbidden is True
    assert authority.no_write_reason == "preserve_visible_surface"
    assert authority.enforced_no_write_categories == ("preserve_visible_surface",)
    assert authority.surface_payload_policy == "none"
    assert authority.ui_surface_action.target_resource_kind == "calendar"


def test_turn_plan_surface_authority_close_uses_nested_surface_action() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "surface_invocation": {
                "intent": "close_visible_surface",
                "primary_surface": "chat",
                "write_behavior": "none",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
                "surface_action": {
                    "type": "close_visible_surface",
                    "status": "requested",
                    "target": "whiteboard",
                    "target_kind": "whiteboard",
                    "target_id": "midterm-study-plan",
                },
            },
        }
    )

    assert authority.is_close is True
    assert authority.surface_action == {
        "type": "close_visible_surface",
        "status": "requested",
        "target": "whiteboard",
        "target_kind": "whiteboard",
        "target_id": "midterm-study-plan",
    }
    assert authority.suppress_auto_graph_writes is True
    assert authority.blocks_artifact_actions is True
    assert authority.blocks_protocol_writes is True
    assert authority.writes_forbidden is True
    assert authority.no_write_reason == "close_visible_surface"
    assert authority.enforced_no_write_categories == ("close_visible_surface",)
    assert authority.surface_payload_policy == "none"


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
        "close_surface_with_write_side_effect",
        "close_surface_has_deletion_semantics",
    }.issubset(_warning_codes(plan))
    assert plan["write_ledger"]["categories"] == [
        "pending_whiteboard_draft",
        "proposed_calendar_task_mutation",
    ]


def test_turn_plan_close_surface_reclassification_warns() -> None:
    plan = _plan(
        message="close the calendar",
        response={
            "surface_action": {"type": "close_visible_surface", "status": "requested", "target": "calendar"},
            "surface_invocation": {
                "intent": "close_visible_surface",
                "primary_surface": "calendar_day",
                "write_behavior": "read_only",
                "whiteboard_mode": "chat",
                "resolved_whiteboard_mode": "chat",
            },
            "active_surface_id": "today-2026-05-13",
            "surface_payloads": [{"id": "today-2026-05-13", "kind": "today_briefing"}],
        },
    )

    assert "close_surface_reclassified" in _warning_codes(plan)


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

    assert "selected_context_open_without_authority" in _warning_codes(plan)


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

    assert "surface_payload_mismatch" in _warning_codes(plan)


def test_turn_plan_surface_authority_operational_surface_builds_payloads() -> None:
    authority = build_turn_plan_surface_authority(
        response_payload={
            "surface_invocation": {
                "intent": "schedule_lookup",
                "primary_surface": "calendar_day",
                "write_behavior": "read_only",
                "resolved_whiteboard_mode": "chat",
            },
        }
    )

    assert authority.is_close is False
    assert authority.is_preserve is False
    assert authority.is_whiteboard_open_only is False
    assert authority.blocks_artifact_actions is False
    assert authority.surface_payload_policy == "build_operational_payload"


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

    assert "mutation_without_confirmation" in _warning_codes(plan)
    assert plan["write_ledger"]["categories"] == ["accepted_calendar_task_mutation"]
    assert plan["write_ledger"]["entries"][0]["committed"] is True


def test_turn_plan_write_ledger_proposed_calendar_task_mutation() -> None:
    plan = _plan(
        message="Move the event.",
        response={
            "surface_invocation": {
                "intent": "calendar_mutation",
                "primary_surface": "calendar_day",
                "write_behavior": "proposal_only",
                "resolved_whiteboard_mode": "chat",
            },
            "artifact_actions": [
                {
                    "id": "action-1",
                    "artifact_kind": "calendar",
                    "operation": "move_event",
                    "status": "proposed",
                    "requires_confirmation": True,
                },
                {
                    "id": "action-2",
                    "artifact_kind": "task",
                    "operation": "create_task",
                    "status": "proposed",
                    "requires_confirmation": True,
                },
            ],
        },
    )

    assert plan["write_ledger"]["categories"] == ["proposed_calendar_task_mutation"]
    assert plan["write_ledger"]["actual_write_effect_count"] == 2
    assert plan["write_ledger"]["committed_write_count"] == 0
    assert plan["write_ledger"]["proposed_write_count"] == 2
    assert plan["validation"]["warnings"] == []


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
    assert plan["write_ledger"]["categories"] == ["open_only_no_write"]
    assert plan["validation"]["status"] == "ok"
    assert plan["validation"]["warnings"] == []
