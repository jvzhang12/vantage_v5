# `tests/test_artifact_actions.py`

Unit tests for Vantage’s generic artifact-action layer and first writable calendar executor.

## Coverage

- Calendar action planning creates a `replace_event` proposal from the visible Today surface without mutating the calendar file.
- Calendar action planning can return an unsaved proposal candidate with `persist=False`, and `save_action_plan()` later writes the same action id and confirmation receipt.
- Calendar capture coverage includes both statement-style events and explicit “calendar event ... called ...” phrasing, while lookup phrasing such as “show me my calendar” stays action-free.
- Task capture coverage verifies that meaningful leading verbs such as “create” remain in task titles for prompts like “Add a task to create slides tonight.”
- Ambiguous visible calendar matches are rejected with clarification text.
- Read-only calendar providers do not produce writable actions.
- Accepted calendar actions commit through the writable local calendar provider.

## Why It Matters

These tests lock in the safety model for operational artifacts: Vantage can understand and stage edits, but mutation only happens after a validated action is accepted against the user-scoped provider.
