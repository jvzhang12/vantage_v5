# `src/vantage_v5/services/whiteboard_routing.py`

Narrow whiteboard routing rules shared by context preparation and turn orchestration.

## Purpose

- Keep whiteboard phrase matching and mode resolution outside the HTTP server.
- Preserve the existing explicit whiteboard, current-draft edit, and pending whiteboard carry rules without expanding into broad deterministic intent sorting.
- Provide one reusable collaborator for `ContextSupport` and `TurnOrchestrator`.

## Key Classes

- `WhiteboardRoutingEngine`: resolves whiteboard mode, detects explicit whiteboard draft/open requests, detects current-draft edit follow-ups, and decides whether pending whiteboard offers/drafts carry.

## Notable Behavior

- Fresh explicit whiteboard draft requests do not accidentally carry stale pending whiteboard context.
- Explicit open phrasing includes `fresh`, `new`, `blank`, `empty`, and `shared` whiteboard variants, so direct requests such as `open a fresh whiteboard and draft...` go straight to draft mode.
- Short acceptance, deictic, and targeted edit follow-ups can carry an active pending whiteboard update when the pending payload includes the original user message.
- Long or generic follow-ups are rejected to keep hidden and stale whiteboard context from leaking.
