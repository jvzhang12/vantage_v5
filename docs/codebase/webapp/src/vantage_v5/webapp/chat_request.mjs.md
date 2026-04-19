# `src/vantage_v5/webapp/chat_request.mjs`

Small helper module for deciding when the current whiteboard should be included in `/api/chat` requests.

## Purpose

- Detect explicit whiteboard requests in natural language.
- Decide when a pending whiteboard offer/draft should carry into the next turn.
- Build the canonical workspace context payload sent to the backend.

## Key Functions

- `isExplicitWhiteboardRequest()`
- `shouldCarryPendingWorkspaceUpdate()`
- `deriveWorkspaceContextScope()`
- `buildWorkspaceContextPayload()`

## Notable Behavior

- Keeps hidden whiteboards out of normal chat by default.
- Treats only a focused whiteboard as in scope for chat payloads; `Vantage` opened from the whiteboard preserves the return path but does not silently make the whiteboard visible/in scope to the backend.
- Matches the server’s narrow explicit-whiteboard phrasing for `open whiteboard` and `draft ... in/on/into the whiteboard`, instead of treating any `whiteboard` mention as a drafting request.
- Uses the same pending whiteboard carry matcher as the backend’s current deterministic contract: explicit whiteboard requests, the small acceptance phrase list, or edit verbs targeting the current draft.
- Supports an explicit force override for the dedicated accept-button flow, so `/api/chat/whiteboard/accept` does not depend on the ordinary chat carry matcher.
- Uses the current surface plus optional pin/request hints to choose the canonical request scope, while still allowing an explicit `auto` override when a caller wants the backend to decide.
- Only includes `workspace_content` when the resulting scope is intentionally in scope for the turn: `visible`, `pinned`, or `requested`.
