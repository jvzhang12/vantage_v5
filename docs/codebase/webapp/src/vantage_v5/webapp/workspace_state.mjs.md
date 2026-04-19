# `src/vantage_v5/webapp/workspace_state.mjs`

Tiny helper for whiteboard snapshot and preservation rules.

## Purpose

- Normalize the client’s whiteboard state into a serializable snapshot shape.
- Decide when a dirty local whiteboard should win over a passive backend workspace refresh.

## Key Functions

- `buildWorkspaceSnapshot()`
- `shouldPreserveUnsavedWorkspace()`

## Notable Behavior

- Snapshot state includes `workspaceId`, `scope`, `title`, `content`, `savedContent`, `dirty`, `pinnedToChat`, `lifecycle`, and `note`, which is enough for `app.js` to restore both whiteboard copy and lifecycle cues from session storage.
- Defaults dirty snapshots to `transient_draft` and keeps `savedContent` empty unless the caller explicitly supplied the saved baseline, which preserves unsaved-draft semantics across local snapshot restore.
- Protects unsaved local whiteboards from being replaced by passive refreshes only when the incoming workspace still matches the current scope and saved baseline, so unrelated saved workspaces do not silently overwrite the draft-protection rule.
