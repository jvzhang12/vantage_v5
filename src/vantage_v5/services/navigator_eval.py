from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


VALID_ROUTES = {"chat", "scenario_lab"}
VALID_DRAFT_SURFACES = {"none", "offer_whiteboard", "draft_whiteboard", "auto"}


@dataclass(frozen=True, slots=True)
class NavigatorEvalCase:
    id: str
    message: str
    history: list[dict[str, str]]
    requested_whiteboard_mode: str
    workspace: dict[str, Any]
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None
    pending_workspace_update: dict[str, Any] | None
    continuity_context: dict[str, Any] | None
    expect: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NavigatorEvalResult:
    case_id: str
    passed: bool
    expected: dict[str, Any]
    actual: dict[str, Any]
    failures: tuple[str, ...]
    raw_decision: dict[str, Any] | None = None


def load_navigator_eval_cases(path: Path) -> list[NavigatorEvalCase]:
    cases: list[NavigatorEvalCase] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        payload = json.loads(line)
        cases.append(_case_from_payload(payload, path=path, line_number=line_number))
    return cases


def summarize_navigation_decision(decision: Any) -> dict[str, Any]:
    route = "scenario_lab" if decision.mode == "scenario_lab" else "chat"
    return {
        "route": route,
        "draft_surface": "none" if route == "scenario_lab" else _draft_surface(decision.whiteboard_mode),
        "protocols": _protocols_from_control_panel(decision.control_panel),
        "preserve_context": bool(
            decision.preserve_pinned_context
            if decision.preserve_pinned_context is not None
            else decision.preserve_selected_record
        ),
    }


def evaluate_navigation_summary(
    case: NavigatorEvalCase,
    actual: dict[str, Any],
    *,
    raw_decision: dict[str, Any] | None = None,
) -> NavigatorEvalResult:
    expected = normalize_expected_summary(case.expect)
    normalized_actual = normalize_actual_summary(actual)
    failures = tuple(_summary_failures(expected=expected, actual=normalized_actual))
    return NavigatorEvalResult(
        case_id=case.id,
        passed=not failures,
        expected=expected,
        actual=normalized_actual,
        failures=failures,
        raw_decision=raw_decision,
    )


def normalize_expected_summary(value: dict[str, Any]) -> dict[str, Any]:
    route = str(value.get("route") or "").strip()
    draft_surface = str(value.get("draft_surface") or "none").strip()
    if route not in VALID_ROUTES:
        raise ValueError(f"Navigator eval expected route must be one of {sorted(VALID_ROUTES)}.")
    if draft_surface not in VALID_DRAFT_SURFACES:
        raise ValueError(
            f"Navigator eval expected draft_surface must be one of {sorted(VALID_DRAFT_SURFACES)}."
        )
    return {
        "route": route,
        "draft_surface": draft_surface,
        "protocols": sorted({str(item).strip() for item in value.get("protocols", []) if str(item).strip()}),
        "preserve_context": bool(value.get("preserve_context", False)),
    }


def normalize_actual_summary(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": str(value.get("route") or "chat").strip(),
        "draft_surface": str(value.get("draft_surface") or "none").strip(),
        "protocols": sorted({str(item).strip() for item in value.get("protocols", []) if str(item).strip()}),
        "preserve_context": bool(value.get("preserve_context", False)),
    }


def results_payload(results: Iterable[NavigatorEvalResult]) -> dict[str, Any]:
    result_list = list(results)
    return {
        "passed": sum(1 for result in result_list if result.passed),
        "failed": sum(1 for result in result_list if not result.passed),
        "results": [
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "expected": result.expected,
                "actual": result.actual,
                "failures": list(result.failures),
                "raw_decision": result.raw_decision,
            }
            for result in result_list
        ],
    }


def _case_from_payload(payload: dict[str, Any], *, path: Path, line_number: int) -> NavigatorEvalCase:
    case_id = str(payload.get("id") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not case_id or not message:
        raise ValueError(f"{path}:{line_number} navigator eval cases require non-empty id and message.")
    expect = payload.get("expect")
    if not isinstance(expect, dict):
        raise ValueError(f"{path}:{line_number} navigator eval case requires an expect object.")
    normalize_expected_summary(expect)
    return NavigatorEvalCase(
        id=case_id,
        message=message,
        history=_history_from_payload(payload.get("history")),
        requested_whiteboard_mode=str(payload.get("requested_whiteboard_mode") or "auto").strip() or "auto",
        workspace=payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {},
        pinned_context_id=str(payload.get("pinned_context_id") or "").strip() or None,
        pinned_context=payload.get("pinned_context") if isinstance(payload.get("pinned_context"), dict) else None,
        pending_workspace_update=(
            payload.get("pending_workspace_update")
            if isinstance(payload.get("pending_workspace_update"), dict)
            else None
        ),
        continuity_context=(
            payload.get("continuity_context") if isinstance(payload.get("continuity_context"), dict) else None
        ),
        expect=expect,
    )


def _history_from_payload(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    history: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role and content:
            history.append({"role": role, "content": content})
    return history


def _draft_surface(whiteboard_mode: str | None) -> str:
    if whiteboard_mode == "offer":
        return "offer_whiteboard"
    if whiteboard_mode == "draft":
        return "draft_whiteboard"
    if whiteboard_mode == "auto":
        return "auto"
    return "none"


def _protocols_from_control_panel(control_panel: dict[str, Any]) -> list[str]:
    actions = control_panel.get("actions") if isinstance(control_panel, dict) else None
    if not isinstance(actions, list):
        return []
    protocols: set[str] = set()
    for action in actions:
        if not isinstance(action, dict) or action.get("type") != "apply_protocol":
            continue
        protocol_kind = str(action.get("protocol_kind") or "").strip()
        if protocol_kind:
            protocols.add(protocol_kind)
    return sorted(protocols)


def _summary_failures(*, expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in ("route", "draft_surface", "preserve_context"):
        if actual[key] != expected[key]:
            failures.append(f"{key}: expected {expected[key]!r}, got {actual[key]!r}")
    if actual["protocols"] != expected["protocols"]:
        failures.append(f"protocols: expected {expected['protocols']!r}, got {actual['protocols']!r}")
    return failures
