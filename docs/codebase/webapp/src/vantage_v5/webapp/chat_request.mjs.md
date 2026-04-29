# `src/vantage_v5/webapp/chat_request.mjs`

Small helper module for deciding when the current whiteboard should be included in `/api/chat` requests.

## Purpose

- Detect explicit whiteboard requests in natural language.
- Decide when a pending whiteboard offer/draft should carry into the next turn.
- Build the canonical workspace context payload sent to the backend.

## Key Functions

- `isExplicitWhiteboardRequest()`
- `isDeicticWhiteboardReopenRequest()`
- `resolveWhiteboardReopenTarget()`
- `shouldCarryPendingWorkspaceUpdate()`
- `deriveWorkspaceContextScope()`
- `buildWorkspaceContextPayload()`

## Notable Behavior

- Keeps hidden whiteboards out of normal chat by default.
- Treats only a focused whiteboard as in scope for chat payloads; `Vantage` opened from the whiteboard preserves the return path but does not silently make the whiteboard visible/in scope to the backend.
- Matches the server’s narrow explicit-whiteboard phrasing for `open whiteboard`, `open a fresh/new whiteboard`, and `draft ... in/on/into the whiteboard`, instead of treating any `whiteboard` mention as a drafting request.
- Uses the same pending whiteboard carry matcher as the backend’s current deterministic contract: short acceptance phrases, short continue/resume follow-ups, short edit follow-ups, short deictic follow-up questions like `which one?` or `tell me more`, or only narrow explicit-whiteboard follow-ups that clearly point back to the prior draft/offer, including acceptance-prefixed forms like `okay, open the whiteboard` or `open it, put that in the whiteboard`; fresh explicit whiteboard requests with substantive new content do not carry stale pending context.
- Adds a narrower deictic reopen helper for phrases like `pull that up on the whiteboard` so the client can reopen the one uniquely recalled durable item from the prior turn instead of treating that follow-up like a fresh drafting request against the currently open whiteboard.
- Excludes protocols from deictic whiteboard reopen targets. Protocols may guide a turn, but they are not draft/work-product records to open in the whiteboard.
- Supports an explicit force override for the dedicated accept-button flow, so `/api/chat/whiteboard/accept` does not depend on the ordinary chat carry matcher.
- Uses the current surface plus optional pin/request hints to choose the canonical request scope, while still allowing an explicit `auto` override when a caller wants the backend to decide.
- Keeps hidden whiteboard content out of fresh chat-originated whiteboard requests such as `draft this in the whiteboard`; hidden content is only requested when the user explicitly resumes/continues/reopens the existing whiteboard, pins it, focuses it, or a caller forces the scope.
- Only includes `workspace_content` when the resulting scope is intentionally in scope for the turn: `visible`, `pinned`, or `requested`.
