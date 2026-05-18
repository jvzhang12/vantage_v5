from __future__ import annotations

import pytest

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.surface_invocation import build_surface_invocation


def test_surface_invocation_auto_drafts_email_as_whiteboard_artifact() -> None:
    invocation = build_surface_invocation(user_message="Write an email declining the meeting.")
    payload = invocation.to_dict()

    assert payload["intent"] == "durable_artifact"
    assert payload["primary_surface"] == "whiteboard"
    assert payload["whiteboard_mode"] == "draft"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="chat") == "draft"
    assert "durable work product" in payload["reason"]


def test_surface_invocation_respects_explicit_chat_only() -> None:
    invocation = build_surface_invocation(
        user_message="Write an email declining the meeting, but keep it in chat only.",
        requested_whiteboard_mode="auto",
    )

    assert invocation.intent == "chat_only"
    assert invocation.primary_surface == "chat"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="chat") == "chat"


def test_surface_invocation_calendar_for_today_lookup() -> None:
    invocation = build_surface_invocation(user_message="Tell me about what I have planned for today.")

    assert invocation.intent == "schedule_lookup"
    assert invocation.primary_surface == "calendar_day"
    assert invocation.write_behavior == "read_only"
    assert invocation.whiteboard_mode is None


def test_surface_invocation_chat_mode_does_not_block_operational_surfaces() -> None:
    invocation = build_surface_invocation(
        user_message="What does my day look like?",
        requested_whiteboard_mode="chat",
    )

    assert invocation.intent == "schedule_lookup"
    assert invocation.primary_surface == "calendar_day"
    assert invocation.resolved_whiteboard_mode(requested_mode="chat", current_mode="chat") == "chat"


def test_surface_invocation_calendar_week_for_week_lookup() -> None:
    invocation = build_surface_invocation(user_message="Show me my calendar for this week.")

    assert invocation.intent == "schedule_lookup"
    assert invocation.primary_surface == "calendar_week"
    assert invocation.write_behavior == "read_only"


def test_surface_invocation_multi_surface_for_schedule_planning() -> None:
    invocation = build_surface_invocation(user_message="When should I study for my midterm today?")

    assert invocation.intent == "schedule_planning"
    assert invocation.primary_surface == "calendar_day"
    assert invocation.supporting_surfaces == ("task_focus", "whiteboard")
    assert invocation.write_behavior == "proposal_only"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="chat") == "draft"


def test_surface_invocation_week_for_week_planning() -> None:
    invocation = build_surface_invocation(user_message="Plan my week around homework and studying.")

    assert invocation.intent == "schedule_planning"
    assert invocation.primary_surface == "calendar_week"
    assert invocation.supporting_surfaces == ("task_focus", "whiteboard")


def test_surface_invocation_travel_plan_stays_whiteboard_artifact() -> None:
    invocation = build_surface_invocation(
        user_message="Let us plan a road trip from San Diego to San Francisco over 7 days with 3 sightseeing stops per day."
    )

    assert invocation.intent == "durable_artifact"
    assert invocation.primary_surface == "whiteboard"
    assert invocation.whiteboard_mode == "draft"


def test_surface_invocation_task_focus_for_todos() -> None:
    invocation = build_surface_invocation(user_message="Show my to-do list and what I should focus on.")

    assert invocation.intent == "task_focus"
    assert invocation.primary_surface == "task_focus"
    assert invocation.supporting_surfaces == ()


def test_surface_invocation_remember_control_panel_stays_chat_before_task_focus() -> None:
    invocation = build_surface_invocation(
        user_message="Remember that my graph exam priority is BFS and DFS review.",
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.82,
            reason="Navigator interpreted explicit memory intent.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "remember",
                        "protocol_kind": None,
                        "reason": "The user explicitly asked Vantage to remember information.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
    )

    assert invocation.intent == "memory_write"
    assert invocation.primary_surface == "chat"
    assert invocation.write_behavior == "none"
    assert invocation.whiteboard_mode == "chat"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="chat") == "chat"


def test_surface_invocation_keeps_visible_artifact_for_ambiguous_followup() -> None:
    invocation = build_surface_invocation(
        user_message="What should I do next?",
        visible_artifacts=[{"id": "calendar-day-2026-05-14", "kind": "calendar_day", "title": "Timeline"}],
    )

    assert invocation.intent == "current_artifact_followup"
    assert invocation.primary_surface == "chat"
    assert invocation.whiteboard_mode == "chat"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="draft") == "chat"
    assert invocation.surfaces[0].status == "kept_current_view"


@pytest.mark.parametrize(
    "message",
    [
        "What should I do first from this study plan?",
        "Can you summarize this study plan?",
        "Can you explain this study plan?",
        "What are the key points in this study plan?",
        "Summarize it.",
        "Explain the open artifact.",
    ],
)
def test_surface_invocation_keeps_visible_whiteboard_qna_in_chat(message: str) -> None:
    invocation = build_surface_invocation(
        user_message=message,
        visible_artifacts=[
            {
                "id": "artifact:midterm-study-plan",
                "kind": "whiteboard",
                "title": "Midterm Study Plan",
            }
        ],
    )

    assert invocation.intent == "current_artifact_followup"
    assert invocation.primary_surface == "chat"
    assert invocation.write_behavior == "none"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="draft") == "chat"


def test_surface_invocation_visible_artifact_explicit_whiteboard_draft_still_drafts() -> None:
    invocation = build_surface_invocation(
        user_message="Draft this in the whiteboard.",
        visible_artifacts=[
            {
                "id": "artifact:midterm-study-plan",
                "kind": "whiteboard",
                "title": "Midterm Study Plan",
            }
        ],
    )

    assert invocation.intent == "durable_artifact"
    assert invocation.primary_surface == "whiteboard"
    assert invocation.whiteboard_mode == "draft"


def test_surface_invocation_close_visible_whiteboard_returns_close_action() -> None:
    invocation = build_surface_invocation(
        user_message="close the whiteboard",
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "whiteboard",
                        "reason": "The user asked to close the visible whiteboard.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
        visible_artifacts=[
            {
                "id": "midterm-study-plan",
                "kind": "whiteboard",
                "title": "Midterm Study Plan",
            }
        ],
    )
    payload = invocation.to_dict()

    assert payload["intent"] == "close_visible_surface"
    assert payload["primary_surface"] == "chat"
    assert payload["whiteboard_mode"] == "chat"
    assert payload["write_behavior"] == "none"
    assert payload["surface_action"] == {
        "type": "close_visible_surface",
        "status": "requested",
        "target": "whiteboard",
        "target_id": "midterm-study-plan",
        "target_kind": "whiteboard",
        "title": "Midterm Study Plan",
        "reason": "The user asked to close the visible whiteboard.",
    }


def test_surface_invocation_close_calendar_targets_visible_today() -> None:
    invocation = build_surface_invocation(
        user_message="remove today from view",
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "today",
                        "reason": "The user asked to remove Today from view.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
        visible_artifacts=[
            {
                "id": "today-2026-05-14",
                "kind": "today_briefing",
                "title": "Today",
            }
        ],
    )
    payload = invocation.to_dict()

    assert payload["intent"] == "close_visible_surface"
    assert payload["surface_action"]["target"] == "today"
    assert payload["surface_action"]["target_id"] == "today-2026-05-14"
    assert payload["surface_action"]["target_kind"] == "today_briefing"


def test_surface_invocation_close_without_visible_surface_is_noop_action() -> None:
    invocation = build_surface_invocation(
        user_message="close the whiteboard",
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.91,
            reason="Navigator interpreted a visible-surface close request.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "close_surface",
                        "protocol_kind": None,
                        "target": "whiteboard",
                        "reason": "The user asked to close the visible whiteboard.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
    )
    payload = invocation.to_dict()

    assert payload["intent"] == "close_visible_surface"
    assert payload["surface_action"]["status"] == "no_visible_surface"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="draft") == "chat"


def test_surface_invocation_raw_close_text_without_navigator_action_stays_chat() -> None:
    invocation = build_surface_invocation(
        user_message="don't close the whiteboard",
        visible_artifacts=[
            {
                "id": "midterm-study-plan",
                "kind": "whiteboard",
                "title": "Midterm Study Plan",
            }
        ],
    )
    payload = invocation.to_dict()

    assert payload["intent"] != "close_visible_surface"
    assert "surface_action" not in payload


@pytest.mark.parametrize(
    "message,target",
    [
        ("leave the calendar open", "calendar"),
        ("keep the calendar open", "calendar"),
        ("keep today open", "today"),
        ("leave today open", "today"),
        ("keep the whiteboard open", "whiteboard"),
        ("leave the study plan open", "artifact"),
    ],
)
def test_surface_invocation_preserve_surface_short_circuits_raw_classification(
    message: str,
    target: str,
) -> None:
    invocation = build_surface_invocation(
        user_message=message,
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.86,
            reason="Navigator chose to preserve the visible surface.",
            whiteboard_mode="chat",
            control_panel={
                "actions": [
                    {
                        "type": "preserve_surface",
                        "protocol_kind": None,
                        "target": target,
                        "reason": "The user asked to keep the current surface open.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        ),
        visible_artifacts=[
            {
                "id": "today-2026-05-14" if target in {"calendar", "today"} else "midterm-study-plan",
                "kind": "today_briefing" if target in {"calendar", "today"} else "whiteboard",
                "title": "Today" if target in {"calendar", "today"} else "Midterm Study Plan",
            }
        ],
    )
    payload = invocation.to_dict()

    assert payload["intent"] == "preserve_visible_surface"
    assert payload["primary_surface"] == "chat"
    assert payload["supporting_surfaces"] == []
    assert payload["write_behavior"] == "none"
    assert payload["whiteboard_mode"] == "chat"
    assert payload["surfaces"][0]["status"] == "kept_current_view"
    assert "surface_action" not in payload
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="draft") == "chat"


@pytest.mark.parametrize(
    "message",
    [
        "What should I do first from this study plan?",
        "Can you summarize this study plan?",
    ],
)
def test_surface_invocation_does_not_draft_for_study_plan_noun_only(message: str) -> None:
    invocation = build_surface_invocation(user_message=message)

    assert invocation.primary_surface == "chat"
    assert invocation.write_behavior == "none"
    assert invocation.resolved_whiteboard_mode(requested_mode="auto", current_mode="chat") == "chat"


def test_surface_invocation_code_artifact_summons_code_and_whiteboard() -> None:
    invocation = build_surface_invocation(user_message="Can you implement the calendar endpoint tests?")

    assert invocation.intent == "code_artifact"
    assert invocation.primary_surface == "code_artifact"
    assert invocation.supporting_surfaces == ("whiteboard",)
    assert invocation.whiteboard_mode == "draft"


def test_surface_invocation_defers_to_scenario_lab_route() -> None:
    invocation = build_surface_invocation(
        user_message="Compare three launch paths.",
        navigation=NavigationDecision(
            mode="scenario_lab",
            confidence=0.9,
            reason="Compare options.",
        ),
    )

    assert invocation.intent == "scenario_comparison"
    assert invocation.primary_surface == "chat"
    assert invocation.write_behavior == "artifact_branching"
