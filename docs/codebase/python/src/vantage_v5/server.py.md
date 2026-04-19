# `src/vantage_v5/server.py`

FastAPI application entrypoint for Vantage V5. It wires together configuration, storage backends, search/vetting/chat services, a navigator service, a Scenario Lab service, and the HTML/static web app, then exposes the HTTP API used by the UI and experiment workflow. The current code still uses `workspace_*` names in places, but the product canon should be read as whiteboard / memory trace / working memory / recall.

## Purpose

- Build the app from `AppConfig` and mount the frontend assets under `/static`.
- Serve durable whiteboard state by default, or switch to an active experiment session when one exists.
- Provide API endpoints for health, whiteboard/workspace CRUD, concepts, memory, vault notes, search, promotion/opening actions, experiments, and chat.

## Key Classes / Models

- `ChatRequest`: request body for `/api/chat`, including the generic `selected_record_id`, a canonical `workspace_scope` hint that tells the server whether the current whiteboard should count (`excluded`, `visible`, `pinned`, or `requested`), the current `workspace_content` buffer only when the client wants the live whiteboard in context, `whiteboard_mode` as a UI preference so the composer can explicitly force `offer`, `draft`, `chat`, or leave the decision on `auto`, and optional `pending_workspace_update` metadata so a follow-up “yes / continue” turn can accept a still-open whiteboard invitation semantically instead of losing that context. These `workspace_*` field names are still compatibility aliases for the whiteboard canon.
- `WhiteboardAcceptRequest`: request body for `/api/chat/whiteboard/accept`, mirroring the same `selected_record_id` / `workspace_scope` contract while giving the client an explicit structured acceptance path for a pending whiteboard offer instead of fabricating a hidden chat message; the request must carry the original work-product prompt inside `pending_workspace_update.origin_user_message` so the server can generate the draft from the real request.
- `WorkspaceUpdateRequest`: request body for `/api/workspace`, now with an optional `workspace_id` so the client can save a freshly forked whiteboard draft under a new workspace name instead of overwriting the currently active one.
- `WorkspaceOpenRequest`: request body for `/api/workspace/open`.
- `ConceptPromotionRequest`: request body for `/api/concepts/promote`.
- `ConceptOpenRequest`: request body for `/api/concepts/open`, with `record_id` as the generic alias for saved items.
- `ExperimentStartRequest`: request body for `/api/experiment/start`.

## Key Functions

- `create_app(config: AppConfig | None = None) -> FastAPI`: constructs the app, dependencies, and all routes.
- `main() -> None`: loads config and runs `uvicorn` on `127.0.0.1:{port}`.
- Helper serializers/payload builders:
  - `_serialize_concept_card`
  - `_serialize_saved_note_card`
  - `_serialize_vault_note_card`
  - `_memory_payload`
  - `_workspace_payload`
  - `_session_info`
  - `_runtime`
  - `_selected_record_summary`

## Routes

- `GET /api/health`
- `POST /api/experiment/start`
- `POST /api/experiment/end`
- `GET /api/workspace`
- `POST /api/workspace`
- `POST /api/workspace/open`
- `GET /api/concepts`
- `GET /api/vault-notes`
- `GET /api/memory`
- `GET /api/concepts/search`
- `GET /api/vault-notes/search`
- `GET /api/memory/search`
- `GET /api/memory/{memory_id}`
- `GET /api/concepts/{concept_id}`
- `GET /api/vault-notes/{note_id}`
- `POST /api/concepts/promote`
- `POST /api/concepts/open`
- `POST /api/chat`
- `POST /api/chat/whiteboard/accept`
- `GET /`

## Major Dependencies

- `fastapi`, `FileResponse`, `StaticFiles`, `HTTPException`
- `uvicorn`
- `pydantic.BaseModel` / `Field`
- `vantage_v5.config.AppConfig`
- Services: `ChatService`, `GraphActionExecutor`, `MetaService`, `NavigatorService`, `ScenarioLabService`, `ConceptSearchService`, `ConceptVettingService`
- Storage: `ArtifactStore`, `ConceptStore`, `ExperimentSessionManager`, `MemoryStore`, `MemoryTraceStore`, `ActiveWorkspaceStateStore`, `VaultNoteStore`, `WorkspaceStore`

## Notable Behavior

- Resolves a “runtime” object per request, choosing durable stores or experiment-session stores depending on whether an experiment is active.
- Combines experiment and durable content in several read paths, especially memory/concept lookup and search.
- Uses `HTTPException` to convert missing files into 404s and unexpected chat errors into 500s.
- `/api/chat` now treats `workspace_content` as transient turn context rather than silently persisting it before the reply, and it honors `workspace_scope` so hidden whiteboards do not silently ground ordinary chat. When the whiteboard is in scope, the server overlays the live buffer onto the loaded workspace document; when it is out of scope, the server blanks the workspace content before routing while keeping the active whiteboard id stable.
- `/api/chat` now finalizes turn payloads against the C3 contract before returning them: `learned` stays canonical, `created_record` is backfilled as a thin compatibility alias, `graph_action.record_id` / `concept_id` stay mirrored, pending whiteboard `status` / `type` aliases are normalized both ways, and the selected-item continuity surface is exposed explicitly as top-level `selected_record` plus `selected_record_id`.
- `/api/chat` resolves the selected saved item, concept, memory, or vault note into a compact summary and asks the navigator service for a broader turn interpretation: whether the turn belongs in normal chat or Scenario Lab, whether the selected record should stay anchored for continuity, and what whiteboard hint should guide normal chat.
- Workspace payload helpers now preserve or recompute `scenario_metadata` when a saved branch workspace is hidden for chat scope or overlaid with a live buffer, so the active workspace keeps its stable Scenario Lab identity even when the visible content changes or is blanked.
- `/api/chat` also normalizes an optional pending whiteboard-offer context from the previous turn, but now only carries it forward when the current message matches the same client-side helper rules phrase for phrase: explicit whiteboard requests, short acceptance phrases such as `let's do that` or `that works`, short continue/resume follow-ups that still reference the draft, and short edit-follow-up turns. The server also applies the same length bound as the client so long unrelated messages cannot silently keep carrying stale pending whiteboard state.
- `/api/chat` still writes turn traces under `traces/`, and it now also writes markdown-backed recent-history records under `memory_trace/` so Memory Trace remains distinct from the lower-level debug stream.
- That pending-whiteboard normalization now also backfills `workspace_update.status` from `type` and vice versa, so older pending payloads keep working while `status` remains the canonical field.
- Ordinary `/api/chat` now drops pending whiteboard carry completely when the normalized pending payload does not include `origin_user_message`, which keeps the prompt context truthful and prevents `response_mode` from implying pending-whiteboard grounding when the original work-product request is unavailable.
- `/api/chat` can now also accept an unsaved `workspace_id` together with `workspace_content`; when the file does not exist yet and the whiteboard is in scope, the server builds a transient workspace document from the live buffer instead of failing, which lets the UI chat against a freshly forked whiteboard before the user saves it. If that unsaved workspace is out of scope, the server creates a placeholder document with empty content so normal chat still works instead of erroring.
- Saved artifact payloads, reopened workspaces, and selected-record summaries now all keep `scenario_kind` visible and attach a nested `scenario` object when durable Scenario Lab metadata exists, including branch workspace ids for comparison artifacts and namespace/base-workspace metadata for branch workspaces.
- That selected-record summary lets the navigator keep follow-up questions anchored to an existing Scenario Lab artifact or other selected record instead of re-running branch generation or dropping continuity.
- `/api/chat` deterministically merges explicit UI whiteboard choices with the navigator’s semantic whiteboard hint before it calls `ChatService.reply()`, so interpretation stays LLM-driven while policy and execution stay strict.
- `/api/chat` also includes a narrow deterministic override for explicit user phrasing like “open the whiteboard” or “draft this in the whiteboard”: when the navigator keeps the turn in normal chat, that direct request upgrades auto-mode into `draft` immediately instead of asking for redundant confirmation.
- `/api/chat` now includes a second narrow whiteboard override for live drafting continuity: when the active whiteboard is already in scope with real content and the user is clearly revising that current draft, the server upgrades an ambiguous or over-conservative offer hint into `draft` so Vantage updates the active whiteboard instead of reoffering a new one. That visible-draft matcher stays slightly broader than the pending-carry helper so greeting- or signature-level edits on the active whiteboard still continue the draft naturally.
- `/api/chat/whiteboard/accept` gives the UI a dedicated acceptance route for a pending whiteboard offer, so the client can confirm the collaboration flow without inventing a hidden user turn just to reach the draft path; the route replays the original work-product request from `pending_workspace_update.origin_user_message` so the draft is generated from the real prompt rather than from an opaque acceptance placeholder, and it intentionally bypasses the ordinary stale-carry guard because the acceptance route itself is explicit confirmation.
- `/api/chat` now returns a top-level `turn_interpretation` payload for both normal chat and Scenario Lab turns, giving the UI a compact explanation of the chosen path, requested and resolved whiteboard mode, the source of that whiteboard decision, and selected-record continuity without forcing it to infer those semantics from other fields.
- Scenario Lab turns still save branch workspaces plus a comparison artifact before the payload is returned, and Scenario Lab turns also write first-class Memory Trace records like normal chat.
- `/api/chat` serves the normal retrieval-vetting-response-meta pipeline when the navigator does not send the turn to Scenario Lab, and normal chat can now return non-destructive `workspace_update` metadata either to offer whiteboard collaboration for a work product or to propose a pending draft without mutating the workspace file. Pending draft proposals now use the canonical status `draft_ready`, which lets the frontend drop an older `pending -> draft_ready` translation layer.
- If Scenario Lab routing is chosen but the Scenario Lab service throws, `/api/chat` still recovers into normal chat, but the payload now includes an explicit `scenario_lab` failure object plus `scenario_lab_error` so the user-facing UI can explain that Scenario Lab failed after routing.
- `/api/chat` returns the service payload plus whiteboard scope and experiment metadata, now including `workspace.context_scope` so the client can inspect whether the whiteboard actually grounded the turn, and it backfills `workspace.content` when a transient in-scope whiteboard buffer was used even if the turn itself did not generate a new whiteboard proposal. Scenario Lab turns still carry the same truthful `response_mode` structure as normal chat, so the UI can tell when a comparison was grounded by whiteboard, recent-chat, or pending-whiteboard context instead of assuming every Scenario Lab turn is a best guess.
- `ChatService.reply()` now reports a more truthful grounding label for the answer surface: recall-grounded turns stay distinct from whiteboard-only, recent-chat-only, or pending-whiteboard turns, and the visible `This is new to me, but my best guess is:` preface is reserved for truly ungrounded replies.
- `POST /api/workspace` now honors an explicit `workspace_id` and makes that workspace active after saving, which lets accepted drafts become new first-class whiteboards instead of implicitly rewriting the previous active workspace; when that save targets an existing Scenario Lab branch and the edited content omitted the metadata block, the existing branch metadata is preserved so the branch identity survives the save. The route also auto-saves an artifact snapshot for that whiteboard iteration and returns both the workspace payload and the saved artifact metadata.
- `/api/workspace/open` reopens an existing workspace branch by loading it from the active runtime store, switching the active workspace id to that branch, and returning the parsed stable scenario metadata from the workspace store; missing workspace ids now return a 404 instead of bubbling up as a generic server error.
- `/api/concepts/promote` can overwrite workspace content before promoting it into a graph action and artifact record.
- `/api/concepts/open` accepts `record_id` as the generic saved-item alias, keeps `concept_id` for compatibility, and opens the selected item back into the current workspace.
