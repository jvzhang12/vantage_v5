from __future__ import annotations

from vantage_v5.services.response_mode import BEST_GUESS_PREFACE
from vantage_v5.services.response_mode import build_response_mode_payload
from vantage_v5.services.response_mode import finalize_assistant_message


def test_finalize_best_guess_does_not_add_legacy_preface() -> None:
    assert (
        finalize_assistant_message(
            "Use the quieter cyan button treatment.",
            response_mode={"kind": "best_guess"},
        )
        == "Use the quieter cyan button treatment."
    )


def test_finalize_best_guess_strips_legacy_preface_if_present() -> None:
    assert (
        finalize_assistant_message(
            f"{BEST_GUESS_PREFACE}\n\nUse the quieter cyan button treatment.",
            response_mode={"kind": "best_guess"},
        )
        == "Use the quieter cyan button treatment."
    )


def test_finalize_best_guess_strips_punctuated_legacy_preface_variant() -> None:
    assert (
        finalize_assistant_message(
            "This is new to me, but. my best guess is:\nUse the quieter cyan button treatment.",
            response_mode={"kind": "best_guess"},
        )
        == "Use the quieter cyan button treatment."
    )


def test_finalize_grounded_answer_without_preface_is_unchanged() -> None:
    assert (
        finalize_assistant_message(
            "The recalled launch note points toward a quiet cyan treatment.",
            response_mode={"kind": "grounded"},
        )
        == "The recalled launch note points toward a quiet cyan treatment."
    )


def test_response_mode_can_mark_navigator_selected_context() -> None:
    payload = build_response_mode_payload(
        [],
        workspace_has_context=False,
        history_has_context=False,
        attention_has_context=True,
    )

    assert payload["kind"] == "grounded"
    assert payload["grounding_mode"] == "attention"
    assert payload["context_sources"] == ["attention"]
