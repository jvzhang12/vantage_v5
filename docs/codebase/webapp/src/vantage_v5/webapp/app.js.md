# `src/vantage_v5/webapp/app.js`

Main browser entrypoint for the Vantage UI. It owns the client-side state tree, boots the app, talks to the FastAPI API, coordinates chat and whiteboard behavior, and renders the three major surfaces: chat, whiteboard, and `Vantage`.

## Purpose

- Bootstrap health, workspace, catalog, and persisted turn state.
- Manage the client-side state model for surfaces, Recall-facing turn state, Reasoning Path state, Memory Trace inspection state, whiteboard state, experiment state, and notices.
- Send chat requests with the correct workspace scope and pending whiteboard context.
- Render compact chat evidence, whiteboard decisions, guided-inspection summaries, the staged `Reasoning Path` rail, turn-scoped `Recall`, turn-scoped `Memory Trace`, Scenario Lab review, library state, and whiteboard lifecycle cues using the same backend-truth labels in both chat and Vantage.

## Key Responsibilities

- `boot()`, `loadHealth()`, `loadWorkspace()`, `refreshRuntimeStatus()`: startup and passive refresh flow.
- `sendMessage()`, `applyChatPayload()`, `absorbGraphNotices()`: chat request/response loop.
- `applyWorkspacePayload()`, `applyWorkspaceDraft()`, `startFreshWorkspaceDraft()`, `saveWorkspace()`: whiteboard state transitions. `saveWorkspace()` now also consumes the returned artifact snapshot metadata so whiteboard saves leave a visible durable artifact trail in the library and notices.
- `acceptPendingWorkspaceOffer()`, `applyPendingWorkspaceUpdate()`: offer-first whiteboard collaboration flow.
- `currentTurnGrounding()`: thin wrapper over the shared `deriveTurnGrounding()` helper from `product_identity.mjs`, so the app consumes one normalized grounding view-model instead of re-deriving counts and labels locally.
- `renderTurnPanel()`: central Vantage answer-dock render path for grounding summary, Reasoning Path, whiteboard update disclosure, Memory Trace, Recall, and Learned.
- `renderReasoningPathPanel()`: renders the staged inspection rail and stage drill-down panels from the `buildReasoningPathInspection()` view model.
- `renderMemoryTracePanel()`: renders recent-history contribution plus the created turn trace record without turning Memory Trace into a general library surface.
- `renderScenarioLabPanel()`: renders the Scenario Lab review surface with comparison question, recommendation, tradeoffs, branch paths, and the saved comparison artifact.
- `createScenarioTranscriptCard()`: adds a compact Scenario Lab result card directly in chat so the mode is legible before the user opens `Vantage`.
- `persistTurnSnapshot()` / `restoreTurnSnapshot()`: session-scoped client continuity.

## Notable Behavior

- Uses the explicit surface enum from `surface_state.mjs` instead of interacting booleans.
- Keeps the whiteboard separate from `Vantage` inspection, with whiteboard-focused layout when drafting.
- Reuses the same response-mode truth for compact chat evidence and the Vantage summary so the product difference stays visible without a full inspection click.
- Centralizes turn grounding in the shared helper stack so the Vantage summary, turn panel, and Scenario Lab panel all consume the same normalized `response_mode` instead of re-deriving grounding semantics independently.
- Persists more than the visible draft: session snapshots are keyed by `{scope, experimentSessionId, workspaceId}` and also keep the active Reasoning Path stage, turn-scoped Memory Trace cards, candidate trace notes, and other turn inspection state.
- Keeps `Recall` distinct from broader `Working Memory` framing in the inspection UI: `state.turnWorkingMemory` holds the surfaced recalled-item subset, while the `Working Memory` dock summary and Reasoning Path scope table explain the broader generation context.
- Carries `candidate_trace_notes` into the Candidate context stage and `trace_notes` plus `memory_trace_record` into the Memory Trace section, so recent-history consideration, selected recent-history contribution, and the created turn trace record remain separate concepts in the UI.
- Reuses the existing card renderer inside Recall, Memory Trace, and Reasoning Path drill-down groups, but keeps `memory_trace` cards inspect-only and suppresses whiteboard-opening actions for stage drill-down cards.
- Uses the normalized interpretation payload directly in the Route stage, including requested whiteboard mode, resolved whiteboard mode, decision source, confidence, and selected-record continuity.
- Trusts the canonical normalized `recallCount` for grounding summaries instead of relying only on the currently visible recalled-item array length.
- Uses top-level turn Recall, Learned, and response-mode state when describing Scenario Lab grounding, rather than assuming those fields live inside the Scenario Lab payload itself.
- Frames Scenario Lab as a dedicated comparison-first reasoning surface, separate from the Working Memory dock, and surfaces a compact open-the-lab card in chat for successful Scenario Lab turns.
- Treats unsaved dirty whiteboards as authoritative during passive refresh so the backend's last saved workspace does not erase a local draft.
- Stores both workspace-scoped and scope-scoped turn snapshots so temporary unsaved drafts can survive across refreshes and workspace-id changes.
- Treats whiteboard offers and draft proposals as pending decisions until the user applies or accepts them.
- When the backend returns an auto-saved artifact snapshot for a whiteboard save, the client upserts it into the saved-note catalog and surfaces a dedicated notice without changing the whiteboard lifecycle into a promoted artifact.
- Routes reveal/hide whiteboard transitions through the shared surface helpers rather than ad hoc `{ current, returnSurface }` assignments.
- Forces pending whiteboard context explicitly for the dedicated accept-button flow, so `/api/chat/whiteboard/accept` does not rely on the ordinary chat carry matcher for empty-message acceptance.
- Uses canonical `record_id` when opening saved items into the whiteboard, while keeping any remaining id-compatibility fallback centralized in the DTO helpers instead of spread across DOM code.
