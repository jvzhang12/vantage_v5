from __future__ import annotations

from pathlib import Path

import pytest

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator_eval import evaluate_navigation_summary
from vantage_v5.services.navigator_eval import load_navigator_eval_cases
from vantage_v5.services.navigator_eval import normalize_expected_summary
from vantage_v5.services.navigator_eval import results_payload
from vantage_v5.services.navigator_eval import summarize_navigation_decision


REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "evals" / "navigator_cases.jsonl"


def test_navigator_eval_cases_are_small_behavior_contracts() -> None:
    cases = load_navigator_eval_cases(CASES_PATH)

    assert len(cases) >= 8
    assert {case.id for case in cases} >= {
        "email_work_product_offer",
        "explicit_whiteboard_draft",
        "scenario_lab_compare_paths",
        "ordinary_question_stays_chat",
    }
    for case in cases:
        expected = normalize_expected_summary(case.expect)
        assert set(expected) == {"route", "draft_surface", "protocols", "preserve_context"}


def test_summarize_navigation_decision_reduces_payload_to_product_behavior() -> None:
    decision = NavigationDecision(
        mode="chat",
        confidence=0.8,
        reason="Draft an email with protocol guidance.",
        whiteboard_mode="offer",
        preserve_pinned_context=None,
        control_panel={
            "actions": [
                {"type": "respond", "protocol_kind": None},
                {"type": "apply_protocol", "protocol_kind": "email"},
                {"type": "apply_protocol", "protocol_kind": "email"},
            ]
        },
    )

    assert summarize_navigation_decision(decision) == {
        "route": "chat",
        "draft_surface": "offer_whiteboard",
        "protocols": ["email"],
        "preserve_context": False,
    }


def test_summarize_navigation_decision_ignores_whiteboard_mode_for_scenario_lab() -> None:
    decision = NavigationDecision(
        mode="scenario_lab",
        confidence=0.8,
        reason="Compare alternatives.",
        whiteboard_mode="auto",
        control_panel={
            "actions": [
                {"type": "apply_protocol", "protocol_kind": "scenario_lab"},
                {"type": "open_scenario_lab", "protocol_kind": None},
            ]
        },
    )

    assert summarize_navigation_decision(decision) == {
        "route": "scenario_lab",
        "draft_surface": "none",
        "protocols": ["scenario_lab"],
        "preserve_context": False,
    }


def test_evaluate_navigation_summary_reports_compact_failures() -> None:
    case = load_navigator_eval_cases(CASES_PATH)[0]

    result = evaluate_navigation_summary(
        case,
        {
            "route": "chat",
            "draft_surface": "none",
            "protocols": [],
            "preserve_context": False,
        },
    )

    assert result.passed is False
    assert result.failures == (
        "draft_surface: expected 'offer_whiteboard', got 'none'",
        "protocols: expected ['email'], got []",
    )


def test_results_payload_counts_passes_and_failures() -> None:
    case = load_navigator_eval_cases(CASES_PATH)[0]
    passing = evaluate_navigation_summary(case, normalize_expected_summary(case.expect))
    failing = evaluate_navigation_summary(case, {"route": "chat", "draft_surface": "none"})

    assert results_payload([passing, failing])["passed"] == 1
    assert results_payload([passing, failing])["failed"] == 1


def test_invalid_expected_summary_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_expected_summary({"route": "whiteboard", "draft_surface": "none"})
