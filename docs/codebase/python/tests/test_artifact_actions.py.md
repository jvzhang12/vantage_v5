# `tests/test_artifact_actions.py`

Unit tests for Vantage’s generic artifact-action layer and first writable calendar executor.

## Coverage

- Calendar action planning creates a `replace_event` proposal from the visible Today surface without mutating the calendar file.
- Calendar action planning can return an unsaved proposal candidate with `persist=False`, and `save_action_plan()` later writes the same action id and confirmation receipt.
- Calendar capture coverage includes both statement-style events and explicit “calendar event ... called ...” phrasing, while lookup phrasing such as “show me my calendar” stays action-free.
- Artifact mutation compiler coverage verifies `compiler.source` follows the planner attempt that actually returned an action, including raw-message fallback after an unusable model-normalized command or after a model-normalized task candidate drops a due date recoverable from the raw user message.
- Task capture coverage verifies that meaningful leading verbs such as “create” remain in task titles for prompts like “Add a task to create slides tonight,” that due dates such as “tonight” and “tomorrow” stay in `payload.due_date`, that compiler scaffolding does not leak into task titles, and that reminder-shaped task phrasing is recognized by the task-capture fallback.
- Ambiguous visible calendar matches are rejected with clarification text.
- Read-only calendar providers do not produce writable actions.
- Accepted calendar actions commit through the writable local calendar provider.

## Why It Matters

These tests lock in the safety model for operational artifacts: Vantage can understand and stage edits, but mutation only happens after a validated action is accepted against the user-scoped provider.
