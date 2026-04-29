from __future__ import annotations

from pathlib import Path

import pytest

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.workspaces import WorkspaceDocument


def _decision(*, mode: str = "chat", whiteboard_mode: str | None = None) -> NavigationDecision:
    return NavigationDecision(
        mode=mode,
        confidence=0.9,
        reason="test decision",
        whiteboard_mode=whiteboard_mode,
    )


def _workspace(content: str = "") -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id="test-workspace",
        title="Test Workspace",
        content=content,
        path=Path("test-workspace.md"),
        scenario_metadata=None,
    )


@pytest.mark.parametrize("requested_mode", ["offer", "draft"])
def test_requested_offer_or_draft_wins(requested_mode: str) -> None:
    engine = WhiteboardRoutingEngine()

    assert (
        engine.resolve_whiteboard_mode(
            requested_mode,
            _decision(whiteboard_mode="chat"),
            user_message="What do you think?",
            workspace=_workspace(),
        )
        == requested_mode
    )


def test_requested_chat_wins_even_for_explicit_whiteboard_request() -> None:
    engine = WhiteboardRoutingEngine()

    assert (
        engine.resolve_whiteboard_mode(
            "chat",
            _decision(whiteboard_mode="draft"),
            user_message="Draft this in the whiteboard.",
            workspace=_workspace("Existing draft"),
        )
        == "chat"
    )


def test_explicit_whiteboard_draft_request_upgrades_chat_decision() -> None:
    engine = WhiteboardRoutingEngine()

    assert (
        engine.resolve_whiteboard_mode(
            "auto",
            _decision(mode="chat", whiteboard_mode="chat"),
            user_message="Please outline the launch plan in the whiteboard.",
            workspace=_workspace(),
        )
        == "draft"
    )


def test_current_whiteboard_revision_upgrades_chat_decision_to_draft() -> None:
    engine = WhiteboardRoutingEngine()

    for message in [
        "Tighten the draft and add a warmer greeting.",
        "Make the email warmer and mention that I appreciated the thoughtful feedback.",
        "Replace the current whiteboard content with a concise email draft.",
    ]:
        assert (
            engine.resolve_whiteboard_mode(
                "auto",
                _decision(mode="chat", whiteboard_mode="offer"),
                user_message=message,
                workspace=_workspace("Dear Alex,\n\nHere is the current draft."),
            )
            == "draft"
        )


@pytest.mark.parametrize("navigator_mode", ["chat", "offer", "draft", "auto"])
def test_navigator_whiteboard_mode_is_honored_when_no_override_applies(navigator_mode: str) -> None:
    engine = WhiteboardRoutingEngine()

    assert (
        engine.resolve_whiteboard_mode(
            "auto",
            _decision(mode="chat", whiteboard_mode=navigator_mode),
            user_message="What are the risks?",
            workspace=_workspace(),
        )
        == navigator_mode
    )


@pytest.mark.parametrize("navigator_mode", [None, "invalid"])
def test_resolve_whiteboard_mode_defaults_to_auto_for_unknown_navigator_mode(
    navigator_mode: str | None,
) -> None:
    engine = WhiteboardRoutingEngine()

    assert (
        engine.resolve_whiteboard_mode(
            "auto",
            _decision(mode="chat", whiteboard_mode=navigator_mode),
            user_message="What are the risks?",
            workspace=_workspace(),
        )
        == "auto"
    )


@pytest.mark.parametrize(
    "message",
    [
        "Open the whiteboard for this.",
        "Open a fresh whiteboard and draft a short essay titled Why Design Partner Fit Matters.",
        "Please write the email in the whiteboard.",
        "Let's sketch the launch options on the whiteboard.",
    ],
)
def test_explicit_whiteboard_draft_phrase_detection(message: str) -> None:
    engine = WhiteboardRoutingEngine()

    assert engine.is_explicit_whiteboard_draft_request(message) is True


@pytest.mark.parametrize(
    "message",
    [
        None,
        "",
        "Can we talk through this first?",
        "The whiteboard marker is dry.",
    ],
)
def test_non_explicit_whiteboard_phrases_do_not_trigger_draft(message: str | None) -> None:
    engine = WhiteboardRoutingEngine()

    assert engine.is_explicit_whiteboard_draft_request(message) is False
