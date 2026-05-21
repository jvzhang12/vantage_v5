# `src/vantage_v5/services/artifact_actions.py`

Generic artifact-action planning and execution layer for Vantage.

## Purpose

- Convert explicit user requests such as “replace Advisor check-in with Grocery shopping” into structured, confirmable artifact actions.
- Persist proposed actions in the user-scoped state directory so the UI can later accept or reject by id.
- Keep execution deterministic: model/chat interpretation may shape the request, but only validated local executors mutate data.
- Provide the first concrete executor for user-scoped local calendar JSON.

## Key Classes / Functions

- `ArtifactActionStore`: stores proposed/accepted/rejected action JSON under `state/artifact_actions`.
- `ArtifactActionPlanner`: detects supported artifact mutations and builds proposed calendar/task actions from visible operational surfaces. It resolves relative dates against an explicit app/user timezone-derived `today`; by default it persists proposed actions immediately, but callers can request an unsaved candidate with `persist=False` and later commit it with `save_action_plan()`.
- `execute_artifact_action()`: commits accepted calendar actions through `LocalCalendarProvider`.
- `reject_artifact_action()`: marks a pending action as rejected without mutating data.
- `action_surface_context()` and `action_graph_payload()`: adapt action data for refreshed surfaces and Vantage/Inspect receipts.

## Notable Behavior

- All actions start as `proposed` and require confirmation.
- Relative calendar/task dates such as `today`, `tomorrow`, weekday names, and task `tonight` use the planner's explicit app date rather than the process timezone.
- Unsaved proposal candidates use the same validation and payload shape as persisted proposals, letting higher-level TurnPlan authority inspect candidate safety before an action file is written.
- Calendar actions use visible artifacts first, so the currently displayed calendar day/week is the target context.
- The narrow offline calendar-capture fallback recognizes concrete scheduling statements such as “Add a calendar event tomorrow at 3 PM called Graph study review” and “Add Graph study review at 3 PM tomorrow,” while read-only lookup phrasing such as “show me my calendar” is intentionally skipped so lookup turns do not become proposals. Calendar command-word cleanup is scoped to this fallback path.
- Task capture preserves meaningful leading verbs in task titles, so requests like “create slides” remain task content rather than being stripped as command language. It also normalizes known compiler scaffolding such as `titled "..."`, `due_date`, and confirmation boilerplate out of the task title while keeping due-date parsing separate.
- `is_task_capture_request()` exposes the existing task-capture fallback as a validation signal for upstream orchestration, letting reminder-shaped task commands avoid being double-counted as durable memory writes.
- Supported v1 calendar operations are create, update/rename, move/reschedule, replace, and soft-cancel.
- Ambiguous or missing target events return clarification text instead of an unsafe action.
- Read-only/global configured calendar files are restricted; writable commits are only allowed through the logged-in user’s local calendar provider.
