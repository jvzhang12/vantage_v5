# `tests/test_draft_artifact_lifecycle.py`

Focused unit tests for the Draft/Artifact Lifecycle service.

## Purpose

- Verify saved-item reopen, whiteboard save, snapshot, publish, and promotion flows independently from the HTTP API.
- Lock down lifecycle semantics before more save/publish route code is moved out of `server.py`.

## Coverage

- Reopening concept, memory, and artifact records writes the selected item into the active workspace scope, preserves the generic `open_saved_item_into_workspace` graph action, and sets active workspace state.
- Reopening a durable reference record while an experiment runtime is active writes the whiteboard document into experiment storage, not durable storage.
- Missing saved-item reopen raises `FileNotFoundError` for the HTTP layer to translate.
- Artifact lifecycle card enrichment exposes `artifact_origin` / `artifact_lifecycle` for artifacts, recovers comparison hubs, and does not add artifact-only fields to concepts.
- Saving a visible whiteboard persists the workspace, updates active workspace state, and creates a `whiteboard_snapshot` artifact.
- Saving a workspace update returns the saved workspace plus snapshot graph action and artifact.
- Publishing visible whiteboard content creates a `promoted_artifact` without forcing an unsaved workspace file to exist.
- Promoting an unsaved whiteboard buffer creates a promoted artifact with whiteboard provenance and does not persist the workspace.
