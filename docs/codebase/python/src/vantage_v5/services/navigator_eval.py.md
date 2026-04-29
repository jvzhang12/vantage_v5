# `src/vantage_v5/services/navigator_eval.py`

Small behavior-summary utilities for Navigator evals.

## Purpose

- Keep Navigator evaluation focused on product behavior rather than the full raw `NavigationDecision` payload.
- Let tests and live eval scripts compare a stable summary: route, draft surface, protocols, and pinned-context preservation.

## Key Functions

- `load_navigator_eval_cases(path)`: reads JSONL eval cases and validates their compact expected behavior summaries.
- `summarize_navigation_decision(decision)`: reduces a `NavigationDecision` to `{route, draft_surface, protocols, preserve_context}`.
- `evaluate_navigation_summary(case, actual)`: compares an actual behavior summary to the expected summary and returns compact failure messages.
- `results_payload(results)`: builds aggregate pass/fail output for scripts and reports.

## Contract

The expected summary intentionally ignores rationale text, confidence, action ordering, branch labels, and other metadata. Those fields can still be logged in live reports, but they are not part of default pass/fail because the eval should catch product drift without becoming brittle.

Scenario Lab summaries report `draft_surface: "none"` regardless of any advisory `whiteboard_mode`, because Scenario Lab routing owns the surface and does not use whiteboard drafting hints.
