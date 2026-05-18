from __future__ import annotations

import pytest

from vantage_v5.services.navigator import _normalize_control_panel
from vantage_v5.services.navigator import _stabilize_decision
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.navigator import apply_control_panel_open_intent_fallback
from vantage_v5.storage.workspaces import WorkspaceDocument


def test_control_panel_normalization_validates_actions_and_protocol_kinds() -> None:
    payload = _normalize_control_panel(
        {
            "actions": [
                {"type": "respond", "protocol_kind": "email", "reason": "  answer now  "},
                {"type": "apply_protocol", "kind": "email", "reason": "Use email guidance."},
                {"type": "apply_protocol", "protocol_kind": "unknown"},
                {"type": "delete_everything", "protocol_kind": None},
                {"type": "draft_whiteboard", "protocol_kind": "scenario_lab"},
                {
                    "type": "close_surface",
                    "protocol_kind": "email",
                    "target": "workspace",
                    "target_id": "midterm-study-plan",
                    "confidence": "0.91",
                    "reason": "  close the visible whiteboard  ",
                },
                {
                    "type": "preserve_surface",
                    "protocol_kind": "scenario_lab",
                    "target": "study_plan",
                    "reason": "  keep this artifact open  ",
                },
                {"type": "remember", "protocol_kind": "email", "reason": "  remember this fact  "},
            ],
            "working_memory_queries": [" email protocol ", "", "  scenario protocol  "],
            "response_call": {"type": "chat_response", "after_working_memory": True},
        }
    )

    assert payload == {
        "actions": [
            {"type": "respond", "protocol_kind": None, "reason": "answer now"},
            {"type": "apply_protocol", "reason": "Use email guidance.", "protocol_kind": "email"},
            {"type": "draft_whiteboard", "protocol_kind": None},
            {
                "type": "close_surface",
                "protocol_kind": None,
                "target": "whiteboard",
                "target_id": "midterm-study-plan",
                "confidence": 0.91,
                "reason": "close the visible whiteboard",
            },
            {
                "type": "preserve_surface",
                "protocol_kind": None,
                "target": "artifact",
                "reason": "keep this artifact open",
            },
            {"type": "remember", "protocol_kind": None, "reason": "remember this fact"},
        ],
        "working_memory_queries": ["email protocol", "scenario protocol"],
        "response_call": {"type": "chat_response", "after_working_memory": True},
    }


def test_fallback_decision_uses_canonical_control_panel_shape() -> None:
    decision = NavigatorService(model="test-model", openai_api_key=None).route_turn(
        user_message="hello",
        history=[],
        workspace=None,  # type: ignore[arg-type]
    )

    assert decision.mode == "chat"
    assert decision.control_panel["actions"] == [
        {
            "type": "respond",
            "protocol_kind": None,
            "reason": "Fallback routing keeps the turn in chat without pressing other product controls.",
        }
    ]


def test_stabilized_decision_keeps_simple_email_draft_in_chat_with_protocol() -> None:
    decision = _stabilize_decision(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model chose an offer.",
            whiteboard_mode="offer",
            control_panel={
                "actions": [
                    {"type": "open_whiteboard", "protocol_kind": None, "reason": "Model over-offered."},
                ],
                "working_memory_queries": [],
                "response_call": None,
            },
        ),
        user_message="Write an email declining the meeting.",
        requested_whiteboard_mode="auto",
        workspace=WorkspaceDocument(
            workspace_id="eval-whiteboard",
            title="Eval Whiteboard",
            content="",
            path=None,  # type: ignore[arg-type]
        ),
        pending_workspace_update=None,
    )

    assert decision.whiteboard_mode == "chat"
    assert any(
        action["type"] == "apply_protocol" and action["protocol_kind"] == "email"
        for action in decision.control_panel["actions"]
    )
    assert all(action["type"] != "open_whiteboard" for action in decision.control_panel["actions"])


def test_control_panel_fallback_adds_open_intent_for_saved_material_lookup() -> None:
    decision = apply_control_panel_open_intent_fallback(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model selected context but omitted the UI open intent.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
            attention_selection={
                "selected_ids": ["concept:exam-prep", "artifact:midterm-study-plan"],
                "primary_resource_id": "concept:exam-prep",
                "supporting_resource_ids": ["artifact:midterm-study-plan"],
                "rejected_candidate_ids": [],
                "surface_to_open": None,
                "reason": "Use both items as context.",
                "confidence": 0.82,
            },
        ),
        user_message="Show me the saved Midterm Study Plan",
        attention_candidates=[
            {
                "id": "candidate-concept:exam-prep",
                "resource_id": "concept:exam-prep",
                "source": "concept",
                "kind": "concept",
                "app": "concept",
                "suggested_surface": None,
            },
            {
                "id": "candidate-artifact:midterm-study-plan",
                "resource_id": "artifact:midterm-study-plan",
                "source": "artifact",
                "kind": "artifact",
                "app": "whiteboard",
                "suggested_surface": "whiteboard",
            },
        ],
    )

    assert decision.attention_selection is not None
    assert decision.attention_selection["surface_to_open"] == "whiteboard"
    assert decision.attention_selection["selected_ids"] == [
        "concept:exam-prep",
        "artifact:midterm-study-plan",
    ]
    assert any(action["type"] == "open_whiteboard" for action in decision.control_panel["actions"])
    assert decision.whiteboard_mode == "chat"


def test_control_panel_fallback_does_not_open_for_normal_artifact_question() -> None:
    decision = apply_control_panel_open_intent_fallback(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model selected a study plan as context.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
            attention_selection={
                "selected_ids": ["artifact:midterm-study-plan"],
                "primary_resource_id": "artifact:midterm-study-plan",
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": None,
                "reason": "Use the selected study plan as context.",
                "confidence": 0.82,
            },
        ),
        user_message="Can you summarize this study plan?",
        attention_candidates=[
            {
                "id": "candidate-artifact:midterm-study-plan",
                "resource_id": "artifact:midterm-study-plan",
                "source": "artifact",
                "kind": "artifact",
                "app": "whiteboard",
                "suggested_surface": "whiteboard",
            },
        ],
    )

    assert decision.attention_selection is not None
    assert decision.attention_selection["surface_to_open"] is None
    assert all(action["type"] != "open_whiteboard" for action in decision.control_panel["actions"])


def test_control_panel_fallback_adds_memory_intent_and_clears_surface_open() -> None:
    decision = apply_control_panel_open_intent_fallback(
        NavigationDecision(
            mode="chat",
            confidence=0.65,
            reason="Model selected task context because the remembered content mentions priority.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
            attention_selection={
                "selected_ids": ["task_focus:2026-05-14"],
                "primary_resource_id": "task_focus:2026-05-14",
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": "task_focus",
                "reason": "Priority wording matched task focus.",
                "confidence": 0.8,
            },
        ),
        user_message="Remember that my graph exam priority is BFS and DFS review.",
        attention_candidates=[
            {
                "id": "task_focus:2026-05-14",
                "resource_id": "task_focus:2026-05-14",
                "kind": "task_focus",
                "suggested_surface": "task_focus",
            }
        ],
    )

    assert decision.whiteboard_mode == "chat"
    assert decision.attention_selection is not None
    assert decision.attention_selection["surface_to_open"] is None
    assert any(action["type"] == "remember" for action in decision.control_panel["actions"])
    assert all(action["type"] != "open_whiteboard" for action in decision.control_panel["actions"])


@pytest.mark.parametrize(
    "message,expected_target",
    [
        ("keep the whiteboard open", "whiteboard"),
        ("leave the whiteboard open", "whiteboard"),
        ("keep this artifact open", "artifact"),
        ("leave the study plan open", "artifact"),
        ("don't close the whiteboard", "whiteboard"),
    ],
)
def test_control_panel_fallback_preserves_visible_surface_for_keep_open_language(
    message: str,
    expected_target: str,
) -> None:
    decision = apply_control_panel_open_intent_fallback(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model selected unrelated context but did not request a surface action.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [{"type": "respond", "protocol_kind": None, "reason": "Keep answering in chat."}],
                "working_memory_queries": [],
                "response_call": None,
            },
            attention_selection={
                "selected_ids": ["artifact:vantage-demo-one-page-brief"],
                "primary_resource_id": "artifact:vantage-demo-one-page-brief",
                "supporting_resource_ids": [],
                "rejected_candidate_ids": [],
                "surface_to_open": None,
                "reason": "This artifact was selected as possible context.",
                "confidence": 0.82,
            },
        ),
        user_message=message,
        attention_candidates=[
            {
                "id": "candidate-artifact:vantage-demo-one-page-brief",
                "resource_id": "artifact:vantage-demo-one-page-brief",
                "source": "artifact",
                "kind": "artifact",
                "app": "whiteboard",
                "suggested_surface": "whiteboard",
            },
        ],
    )

    assert decision.attention_selection is not None
    assert decision.attention_selection["primary_resource_id"] == "artifact:vantage-demo-one-page-brief"
    assert decision.attention_selection["surface_to_open"] is None
    assert all(action["type"] != "open_whiteboard" for action in decision.control_panel["actions"])
    assert all(action["type"] != "close_surface" for action in decision.control_panel["actions"])
    assert any(
        action["type"] == "preserve_surface" and action["target"] == expected_target
        for action in decision.control_panel["actions"]
    )


def test_stabilized_decision_keeps_simple_message_and_subject_line_drafts_in_chat() -> None:
    for message in [
        "Compose a message to Morgan asking whether Friday still works.",
        "Suggest a subject line for a quick reply to Priya.",
    ]:
        decision = _stabilize_decision(
            NavigationDecision(
                mode="chat",
                confidence=0.8,
                reason="Model chose an offer.",
                whiteboard_mode="offer",
                control_panel={
                    "actions": [
                        {"type": "open_whiteboard", "protocol_kind": None, "reason": "Model over-offered."},
                    ],
                    "working_memory_queries": [],
                    "response_call": None,
                },
            ),
            user_message=message,
            requested_whiteboard_mode="auto",
            workspace=WorkspaceDocument(
                workspace_id="eval-whiteboard",
                title="Eval Whiteboard",
                content="",
                path=None,  # type: ignore[arg-type]
            ),
            pending_workspace_update=None,
        )

        assert decision.whiteboard_mode == "chat"
        assert [action["protocol_kind"] for action in decision.control_panel["actions"]] == ["email"]


def test_stabilized_decision_keeps_chat_only_but_applies_email_protocol() -> None:
    decision = _stabilize_decision(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model chose plain chat.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
        ),
        user_message="Write an email declining the meeting, but keep the full draft in chat only.",
        requested_whiteboard_mode="auto",
        workspace=WorkspaceDocument(
            workspace_id="eval-whiteboard",
            title="Eval Whiteboard",
            content="",
            path=None,  # type: ignore[arg-type]
        ),
        pending_workspace_update=None,
    )

    assert decision.whiteboard_mode == "chat"
    assert [action["protocol_kind"] for action in decision.control_panel["actions"]] == ["email"]


def test_stabilized_decision_offers_whiteboard_for_complex_work_products() -> None:
    for message, expected_protocol in [
        ("Plan a two-day Seattle itinerary focused on vegetarian food and indie bookstores.", None),
        ("Draft a short research paper introduction about representation learning.", "research_paper"),
        ("Create a launch checklist for next week's release.", None),
        ("Write a quarterly report about beta feedback.", None),
        ("Write a report about email subject-line conventions.", None),
    ]:
        decision = _stabilize_decision(
            NavigationDecision(
                mode="chat",
                confidence=0.8,
                reason="Model chose plain chat.",
                whiteboard_mode="chat",
                control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
            ),
            user_message=message,
            requested_whiteboard_mode="auto",
            workspace=WorkspaceDocument(
                workspace_id="eval-whiteboard",
                title="Eval Whiteboard",
                content="",
                path=None,  # type: ignore[arg-type]
            ),
            pending_workspace_update=None,
        )

        assert decision.whiteboard_mode == "offer"
        assert any(action["type"] == "open_whiteboard" for action in decision.control_panel["actions"])
        if expected_protocol:
            assert any(
                action["type"] == "apply_protocol" and action["protocol_kind"] == expected_protocol
                for action in decision.control_panel["actions"]
            )


def test_stabilized_decision_offers_for_multi_option_or_saved_email_docs() -> None:
    for message in [
        "Draft three versions of an email declining the meeting.",
        "Write an email to Amy thanking her for the flowers and save it for later.",
    ]:
        decision = _stabilize_decision(
            NavigationDecision(
                mode="chat",
                confidence=0.8,
                reason="Model chose plain chat.",
                whiteboard_mode="chat",
                control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
            ),
            user_message=message,
            requested_whiteboard_mode="auto",
            workspace=WorkspaceDocument(
                workspace_id="eval-whiteboard",
                title="Eval Whiteboard",
                content="",
                path=None,  # type: ignore[arg-type]
            ),
            pending_workspace_update=None,
        )

        assert decision.whiteboard_mode == "offer"
        assert {action["type"] for action in decision.control_panel["actions"]} >= {"apply_protocol", "open_whiteboard"}


def test_stabilized_decision_respects_explicit_whiteboard_for_simple_email() -> None:
    decision = _stabilize_decision(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model chose plain chat.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
        ),
        user_message="Draft an email declining the meeting in the whiteboard.",
        requested_whiteboard_mode="auto",
        workspace=WorkspaceDocument(
            workspace_id="eval-whiteboard",
            title="Eval Whiteboard",
            content="",
            path=None,  # type: ignore[arg-type]
        ),
        pending_workspace_update=None,
    )

    assert decision.whiteboard_mode == "draft"
    assert {action["type"] for action in decision.control_panel["actions"]} >= {"apply_protocol", "draft_whiteboard"}


def test_stabilized_decision_drafts_active_email_revision() -> None:
    decision = _stabilize_decision(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model chose plain chat.",
            whiteboard_mode="chat",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
        ),
        user_message="Tighten the greeting and make the tone warmer.",
        requested_whiteboard_mode="auto",
        workspace=WorkspaceDocument(
            workspace_id="email-draft",
            title="Email Draft",
            content="# Email Draft\n\nDear Maya,\n\nThanks for testing the beta.\n\nBest,\nJordan",
            path=None,  # type: ignore[arg-type]
        ),
        pending_workspace_update=None,
    )

    assert decision.whiteboard_mode == "draft"
    assert {action["type"] for action in decision.control_panel["actions"]} >= {"apply_protocol", "draft_whiteboard"}


def test_stabilized_decision_drafts_active_email_make_and_mention_revision() -> None:
    decision = _stabilize_decision(
        NavigationDecision(
            mode="chat",
            confidence=0.8,
            reason="Model chose an offer.",
            whiteboard_mode="offer",
            control_panel={"actions": [], "working_memory_queries": [], "response_call": None},
        ),
        user_message="Make the email warmer and mention that I appreciated the thoughtful feedback.",
        requested_whiteboard_mode="auto",
        workspace=WorkspaceDocument(
            workspace_id="email-draft",
            title="Email Draft",
            content="# Email Draft\n\nHi Morgan,\n\nWould you join the beta?\n\nBest,\nJordan",
            path=None,  # type: ignore[arg-type]
        ),
        pending_workspace_update=None,
    )

    assert decision.whiteboard_mode == "draft"
    assert {action["type"] for action in decision.control_panel["actions"]} >= {"apply_protocol", "draft_whiteboard"}
