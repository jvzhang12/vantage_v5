# `src/vantage_v5/webapp/whiteboard_decisions.mjs`

Whiteboard-decision presentation logic extracted from `app.js`.

## Purpose

- Decide whether a workspace offer/draft still needs user resolution.
- Build the action set shown in the whiteboard decision panel.
- Keep chat-side workspace-update UI hidden when the whiteboard owns the decision surface.

## Key Functions

- `normalizeWorkspaceDecision()`
- `isWorkspaceResolutionDecision()`
- `hasPendingWorkspaceDecision()`
- `workspaceUpdateHasDraft()`
- `shouldHideChatWorkspaceUpdate()`
- `deriveWhiteboardDecisionPresentation()`

## Notable Behavior

- Re-exports `isWhiteboardFocused()` from `surface_state.mjs` so decision visibility follows the same canonical surface enum the rest of the client uses.
- Handles both server-provided pending whiteboard updates and purely local destructive-open decisions such as replacing a dirty draft.
- Keeps the button vocabulary small: replace, append, keep current, open draft, or keep in chat.
- Falls back to a real server `workspace_update` decision when a stale or unrecognized local-decision object is still present, which keeps whiteboard decision UI from disappearing during continuity edge cases.
- Keeps resolved server decisions hidden once the user already chose a path, so chat does not keep surfacing already-applied whiteboard prompts.
