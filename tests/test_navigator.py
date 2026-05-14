from __future__ import annotations

from vantage_v5.services.navigator import _normalize_control_panel
from vantage_v5.services.navigator import _stabilize_decision
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
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
