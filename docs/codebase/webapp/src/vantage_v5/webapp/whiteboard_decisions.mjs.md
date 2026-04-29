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
- `deriveAppliedWorkspaceDraftNote()`
- `shouldHideChatWorkspaceUpdate()`
- `deriveWhiteboardDecisionPresentation()`

## Notable Behavior

- Re-exports `isWhiteboardFocused()` from `surface_state.mjs` so decision visibility follows the same canonical surface enum the rest of the client uses.
- Handles both server-provided pending whiteboard updates and purely local destructive-open decisions such as replacing a dirty draft.
- Keeps the button vocabulary small: replace, append, keep current, open draft, or keep in chat.
- Uses calmer drafting-oriented copy for replace/append/keep decisions, so the whiteboard panel explains what would happen to the current draft without sounding like raw state reconciliation.
- Provides shared status-note copy for applied drafts so forked or reopened drafts do not claim they were newly started from earlier work, while in-place edits still say they updated the current draft.
- Falls back to a real server `workspace_update` decision when a stale or unrecognized local-decision object is still present, which keeps whiteboard decision UI from disappearing during continuity edge cases.
- Keeps resolved server decisions hidden once the user already chose a path, so chat does not keep surfacing already-applied whiteboard prompts.
