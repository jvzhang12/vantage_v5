# `src/vantage_v5/webapp/workspace_state.mjs`

Tiny helper for whiteboard snapshot and preservation rules.

## Purpose

- Normalize the client’s whiteboard state into a serializable snapshot shape.
- Decide when a dirty local whiteboard should win over a passive backend workspace refresh.

## Key Functions

- `buildWorkspaceSnapshot()`
- `shouldPreserveUnsavedWorkspace()`
- `reconcileRestoredWorkspaceAfterLoad()`

## Notable Behavior

- Snapshot state includes `workspaceId`, `scope`, `title`, `content`, `savedContent`, `dirty`, `pinnedToChat`, `lifecycle`, `note`, and the whiteboard-owned latest durable artifact cue, which is enough for `app.js` to restore both whiteboard copy and lifecycle cues from session storage.
- Defaults dirty snapshots to `transient_draft` and keeps `savedContent` empty unless the caller explicitly supplied the saved baseline, which preserves unsaved-draft semantics across local snapshot restore.
- Protects unsaved local whiteboards from being replaced by passive refreshes only when the incoming workspace still matches the current scope and saved baseline, so unrelated saved workspaces do not silently overwrite the draft-protection rule.
- Adds a boot-only reconciliation helper that decides whether the restored draft should win over the freshly loaded workspace and, when the workspace continuity changes or the restore came from the scope-scoped fallback, collapses stale Vantage inspection and clears stale selected-record continuity. Continuity is intentionally stricter than “same workspace id,” but lighter than a byte-for-byte compare: scope and normalized whiteboard content must still match before the client keeps artifact cues or inspected-record state, while harmless title or trailing-whitespace normalization does not drop continuity.
