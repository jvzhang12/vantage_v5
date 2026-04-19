# `src/vantage_v5/storage/state.py`

This module stores the active workspace pointer for the app. `ActiveWorkspaceStateStore` keeps one JSON file at the configured `state_path`, and it exposes two operations: read the current active workspace ID, or write a new active workspace payload.

Reading is intentionally forgiving. If the state file does not exist, the caller gets the supplied default workspace ID. If it does exist, the store parses JSON and uses `active_workspace_id`, again falling back to the default when the field is missing or empty.

Writes are narrow and opinionated. The store always persists a JSON object with `active_workspace_id`, a derived `active_workspace_path` in `workspaces/{id}.md`, and a hard-coded `status: active`. Parent directories are created automatically, so the only real constraint is that the file must be valid JSON when read.
