# `src/vantage_v5/webapp/surface_state.mjs`

Canonical surface-state helper for the client.

## Purpose

- Define the three top-level client surfaces: `chat`, `whiteboard`, and `vantage`.
- Normalize legacy UI state into the current enum-based model.
- Provide helpers for toggling surfaces and determining whether the whiteboard is currently active.
- Generate stable turn-snapshot keys.

## Key Functions

- `normalizeSurfaceState()`
- `isWhiteboardFocused()`
- `hasWhiteboardActiveContext()`
- `revealWhiteboardSurface()`
- `hideWhiteboardSurface()`
- `openVantageSurface()`
- `closeVantageSurface()`
- `toggleWhiteboardSurface()`
- `normalizeRestoredTurnSnapshotState()`
- `buildTurnSnapshotKey()`
- `buildScopedTurnSnapshotKey()`

## Notable Behavior

- Preserves the “return to whiteboard” path when `Vantage` was opened from the whiteboard.
- Treats that return path as navigation state rather than whiteboard-in-scope state, so opening `Vantage` from the whiteboard does not by itself ground ordinary chat with whiteboard content.
- `hasWhiteboardActiveContext()` is intentionally narrow and only returns `true` when the current surface is actually `whiteboard`.
- Also restores that return path from mixed legacy snapshots where `current: "vantage"` survived but only `whiteboardVisible` still described the prior whiteboard context.
- Provides a small restore-policy helper so workspace-scoped snapshots can restore full inspection state while scope-scoped fallback snapshots keep pinned context and draft continuity, clear stale selected-record state, avoid reopening `Vantage` from an older workspace, and preserve the original turn's `workspaceContextScope`.
- Separates workspace-specific snapshot keys from scope-wide snapshot keys so unsaved draft continuity and turn-inspection state are less brittle across refreshes.
