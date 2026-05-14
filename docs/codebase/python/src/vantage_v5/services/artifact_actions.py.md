# `src/vantage_v5/services/artifact_actions.py`

Generic artifact-action planning and execution layer for Vantage.

## Purpose

- Convert explicit user requests such as “replace Advisor check-in with Grocery shopping” into structured, confirmable artifact actions.
- Persist proposed actions in the user-scoped state directory so the UI can later accept or reject by id.
- Keep execution deterministic: model/chat interpretation may shape the request, but only validated local executors mutate data.
- Provide the first concrete executor for user-scoped local calendar JSON.

## Key Classes / Functions

- `ArtifactActionStore`: stores proposed/accepted/rejected action JSON under `state/artifact_actions`.
- `ArtifactActionPlanner`: detects supported artifact mutations and builds proposed calendar actions from visible calendar surfaces.
- `execute_artifact_action()`: commits accepted calendar actions through `LocalCalendarProvider`.
- `reject_artifact_action()`: marks a pending action as rejected without mutating data.
- `action_surface_context()` and `action_graph_payload()`: adapt action data for refreshed surfaces and Vantage/Inspect receipts.

## Notable Behavior

- All actions start as `proposed` and require confirmation.
- Calendar actions use visible artifacts first, so the currently displayed calendar day/week is the target context.
- Supported v1 calendar operations are create, update/rename, move/reschedule, replace, and soft-cancel.
- Ambiguous or missing target events return clarification text instead of an unsafe action.
- Read-only/global configured calendar files are restricted; writable commits are only allowed through the logged-in user’s local calendar provider.
