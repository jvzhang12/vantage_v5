# `src/vantage_v5/services/executor.py`

Executes the graph action chosen by meta decisioning. This service bridges the abstract `MetaDecision` into actual store mutations and returns a normalized status record describing what happened.

## Purpose

- Create concepts, memories, artifacts, and revisions in the appropriate stores.
- Promote a workspace snapshot into a saved artifact.
- Save whiteboard iterations as durable artifact snapshots.
- Re-open saved records into the active workspace.

## Core Data Flow

- `GraphActionExecutor.execute()` receives a `MetaDecision` and the current workspace.
- It dispatches on `decision.action` and writes to the relevant store when the action is supported.
- It wraps each outcome in `ExecutedAction`, which now reports `record_id` and `record_title` while keeping `concept_id` and `concept_title` aliases for compatibility.
- `open_saved_item_into_workspace()` reads a saved record from any available store, formats it as Markdown, saves it into the workspace store, and marks that workspace active.

## Key Classes / Functions

- `ExecutedAction`: normalized result object with action, status, summary, and record-oriented ids.
- `GraphActionExecutor`: performs store writes and workspace promotion/opening.
- `execute()`: main dispatch method for meta actions.
- `promote_workspace()`: direct helper for artifact promotion without going through meta decisioning.
- `save_workspace_iteration_artifact()`: direct helper for durable per-iteration whiteboard artifact snapshots.
- `open_saved_item_into_workspace()`: loads a saved item and writes it into the workspace editor surface.
- `open_concept_into_workspace()`: compatibility alias for the saved-item open path.
- `_get_record()`: searches primary and optional reference stores for a record id.

## Notable Edge Cases

- `no_op` returns `None`, so callers must handle the absence of an executed action.
- `create_revision` is supported here even though it is not one of the visible meta-allowed actions, so callers may still send it from elsewhere.
- Whiteboard iteration snapshots are distinct from `promote_workspace_to_artifact`: the snapshot helper leaves the whiteboard in its normal lifecycle while still writing a durable artifact record for that iteration.
- Revision creation returns `skipped` if `target_concept_id` is missing or if the base concept cannot be found.
- `_get_record()` searches concepts, memories, artifacts, and optional reference stores in order, then raises `FileNotFoundError` if nothing matches.
- `ExecutedAction.to_dict()` exposes both record-oriented keys and the older concept aliases, which keeps existing consumers working if they expect either naming convention.
