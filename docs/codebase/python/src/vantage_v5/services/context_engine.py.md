# `src/vantage_v5/services/context_engine.py`

Backend context-preparation boundary for one chat turn.

## Purpose

- Hide workspace loading, workspace scope normalization, pinned context lookup, pending whiteboard carry, whiteboard entry mode, and Navigator continuity preparation behind one deep interface.
- Return a single `PreparedTurnContext` object to the turn orchestrator so orchestration does not need to know every context-prep detail.
- Keep hidden whiteboard/draft content redacted when the request says workspace context is excluded.

## Key Classes

- `ChatTurnRequestContext`: request-scoped data needed after HTTP validation and alias normalization.
- `PreparedTurnContext`: canonical context object consumed by `TurnOrchestrator`.
- `ContextEngineHooks`: narrow dependency seam for app/runtime-specific lookups: runtime selection plus source-summary callbacks supplied by `ContextSourceResolver`.
- `ContextSourceResolver`: injected app collaborator that resolves pinned-context summaries, whiteboard source summaries, and Navigator continuity context from active/durable stores, vault notes, Memory Trace, and recent whiteboards.
- `ContextSupport`: injected collaborator that owns pure workspace scope, live-buffer, hidden-redaction, pending-whiteboard, and whiteboard-entry helper behavior.
- `ContextEngine`: implements `prepare_turn_context(request_context) -> PreparedTurnContext`.

## Notable Behavior

- `workspace_scope="excluded"` returns a workspace document with empty `content`, even if a saved workspace or unsaved browser buffer exists.
- Missing excluded workspaces are represented as empty unsaved buffers instead of leaking hidden client content or raising.
- Pending whiteboard updates are normalized and carried by `ContextSupport` only when the carry policy says the user is still referring to that pending draft, unless the caller explicitly forces the carry.
