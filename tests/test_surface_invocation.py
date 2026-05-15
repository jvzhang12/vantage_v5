from __future__ import annotations

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


def test_surface_invocation_keeps_visible_artifact_for_ambiguous_followup() -> None:
    invocation = build_surface_invocation(
        user_message="What should I do next?",
        visible_artifacts=[{"id": "calendar-day-2026-05-14", "kind": "calendar_day", "title": "Timeline"}],
    )

    assert invocation.intent == "current_artifact_followup"
    assert invocation.primary_surface == "chat"
    assert invocation.surfaces[0].status == "kept_current_view"


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
