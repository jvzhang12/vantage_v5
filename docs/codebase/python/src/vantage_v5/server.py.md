# `src/vantage_v5/server.py`

FastAPI application entrypoint for Vantage V5. It wires together configuration, storage backends, search/vetting/chat services, a navigator service, a Scenario Lab service, and the HTML/static web app, then exposes the HTTP API used by the UI and experiment workflow. The current code still uses some compatibility aliases, but the product canon should be read as whiteboard / memory trace / working memory / recall with pinned-context continuity as the public/client seam.

## Purpose

- Build the app from `AppConfig` and mount the frontend assets under `/static`.
- Serve durable whiteboard state by default, switch to an active experiment session when one exists, and isolate durable/experiment state per authenticated user when multi-user profile mode is enabled.
- Provide API endpoints for health, account creation, login/logout, per-user OpenAI key status/save/clear, whiteboard/workspace CRUD, concepts, protocols, memory, vault notes, search, promotion/opening actions, experiments, and chat.
- Delegate `/api/chat` context preparation to `ContextEngine` plus `ContextSupport`, source/continuity lookup to `ContextSourceResolver`, protocol action and API catalog/update semantics to `ProtocolEngine`, local semantic actions to `LocalSemanticActionEngine`, turn execution to `TurnOrchestrator`, whiteboard phrase routing to `WhiteboardRoutingEngine`, draft/artifact lifecycle work to `DraftArtifactLifecycle`, record-card presentation to `record_cards.py`, and turn payload construction/final compatibility shaping to `turn_payloads.py`.
- Enforce deployment safety checks before exposing the app on non-local hosts, including required auth by default, optional trusted-host enforcement, same-origin protection for mutating browser requests, and secure cookie support for HTTPS reverse proxies.

## Key Classes / Models

- `ChatRequest`: request body for `/api/chat`, including canonical `pinned_context_id` plus legacy `selected_record_id` compatibility, a canonical `workspace_scope` hint that tells the server whether the current whiteboard should count (`excluded`, `visible`, `pinned`, or `requested`), the current `workspace_content` buffer only when the client wants the live whiteboard in context, `whiteboard_mode` as a UI preference so the composer can explicitly force `offer`, `draft`, `chat`, or leave the decision on `auto`, and optional `pending_workspace_update` metadata so a follow-up “yes / continue” turn can accept a still-open whiteboard invitation semantically instead of losing that context. These `workspace_*` field names are still compatibility aliases for the whiteboard canon.
- `WhiteboardAcceptRequest`: request body for `/api/chat/whiteboard/accept`, mirroring the same canonical `pinned_context_id` / `workspace_scope` contract while giving the client an explicit structured acceptance path for a pending whiteboard offer instead of fabricating a hidden chat message; the request must carry the original work-product prompt inside `pending_workspace_update.origin_user_message` so the server can generate the draft from the real request.
- `WorkspaceUpdateRequest`: request body for `/api/workspace`, now with an optional `workspace_id` so the client can save a freshly forked whiteboard draft under a new workspace name instead of overwriting the currently active one.
- `WorkspaceOpenRequest`: request body for `/api/workspace/open`.
- `ConceptPromotionRequest`: request body for `/api/concepts/promote`.
- `ConceptOpenRequest`: request body for `/api/concepts/open`, with `record_id` as the generic alias for saved items.
- `ExperimentStartRequest`: request body for `/api/experiment/start`.
- `ProtocolUpdateRequest`: request body for `PUT /api/protocols/{protocol_kind}`, allowing protocol title, summary card, procedure body, variables, and applies-to phrases to be updated through the Inspect protocol editor.
- `LoginRequest`: request body for cookie-backed username/password login.
- `CreateAccountRequest`: request body for local account creation. Usernames are restricted to path-safe account names, passwords are written only as salted PBKDF2-SHA256 hashes under `state/accounts.json`, and successful creation signs the account into the same cookie-backed session path.
- `OpenAIKeyRequest`: request body for saving a user-entered OpenAI API key. The server trims and stores the key only in memory for the current profile scope, and status responses expose only masked key metadata.

## Key Functions

- `create_app(config: AppConfig | None = None) -> FastAPI`: constructs the app, dependencies, and all routes.
- `main() -> None`: loads config and runs `uvicorn` on the configured `VANTAGE_V5_HOST:{port}`.
- `_chat_turn_response()`: thin compatibility wrapper that builds `ChatTurnRequestContext` and calls `TurnOrchestrator.run()`.
- Helper payload builders:
- `_workspace_payload`
- `_session_info`
- `_runtime`
- `_durable_scope`
- `_requires_public_auth`
- `_request_origin_allowed`

## Routes

- `GET /api/health`
- `POST /api/accounts`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/openai-key`
- `PUT /api/openai-key`
- `DELETE /api/openai-key`
- `POST /api/experiment/start`
- `POST /api/experiment/end`
- `GET /api/workspace`
- `POST /api/workspace`
- `POST /api/workspace/open`
- `GET /api/concepts`
- `GET /api/protocols`
- `GET /api/protocols/{protocol_kind_or_id}`
- `PUT /api/protocols/{protocol_kind}`
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
- `Request` / `Response` for opt-in HTTP Basic Auth middleware
- `vantage_v5.config.AppConfig`
- Services: `ChatService`, `ContextEngine`, `ContextSourceResolver`, `ContextSupport`, `DraftArtifactLifecycle`, `GraphActionExecutor`, `LocalSemanticActionEngine`, `MetaService`, `NavigatorService`, `ProtocolEngine`, `ScenarioLabService`, `ConceptSearchService`, `ConceptVettingService`, `TurnOrchestrator`, `WhiteboardRoutingEngine`, record-card presentation helpers, and backend turn-payload assembly helpers.
- Storage: `ArtifactStore`, `ConceptStore`, `ExperimentSessionManager`, `MemoryStore`, `MemoryTraceStore`, `ActiveWorkspaceStateStore`, `VaultNoteStore`, `WorkspaceStore`

## Notable Behavior

- Preserves the original single-user storage layout when no multi-user credential map is configured.
- When `auth_users` is configured, Basic Auth usernames are normalized into safe storage ids and each user gets isolated Markdown-backed `concepts/`, `memories/`, `artifacts/`, `workspaces/`, `memory_trace/`, `state/`, and `traces/` directories under `users/<username>/`.
- Adds a read-through canonical default layer under `canonical/`: profile and experiment stores stay private/writable, while canonical concepts, protocols, memories, and artifacts are visible as lower-priority reference context without being copied into each user folder.
- Refuses non-local bind hosts such as `0.0.0.0` unless auth is enabled, unless `VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH=true` is explicitly set.
- Supports optional `TrustedHostMiddleware` through `VANTAGE_V5_ALLOWED_HOSTS`.
- Blocks mutating cross-origin requests when an `Origin` or `Referer` does not match the request host or configured `VANTAGE_V5_ALLOWED_ORIGINS`.
- Sets login cookies with `Secure` when `VANTAGE_V5_COOKIE_SECURE=true`, which is the expected setting behind an HTTPS proxy or tunnel.
- `/api/health` remains unauthenticated for uptime checks, but includes the current user only when a valid Basic Auth header or login cookie is supplied. It also reports masked OpenAI key status, using the environment key for unauthenticated checks and the current user's in-memory override after login.
- `/api/accounts` creates local username/password accounts when auth/profile mode is enabled. It rejects usernames that collide with configured auth users or existing local accounts, hashes passwords before writing `state/accounts.json`, seeds the new user's private storage root, and returns a login cookie so the user lands in their own durable session immediately. Canonical defaults remain read-through references rather than copied account files.
- `/api/openai-key` lets an authenticated profile inspect masked key status, save a session-local user key, or clear that key back to the environment/fallback setting. Full key material is never returned in API responses and is not written to the Markdown-backed user store.
- Chat, Scenario Lab, Navigator, vetting, meta, and protocol interpreter services are now constructed from the effective key for the current durable scope, so a saved user key affects the model-backed request path without requiring a server restart.

- Resolves a “runtime” object per request, choosing durable stores or experiment-session stores depending on whether an experiment is active, then layering canonical stores underneath as reference stores.
- When `VANTAGE_V5_AUTH_PASSWORD` is configured, protects the UI, static assets, and API routes with HTTP Basic Auth while leaving `/api/health` open for host health checks.
- Combines experiment, durable, and canonical content in several read paths, especially memory/concept lookup, protocol catalogs, and search. Higher-priority user/session records override canonical records with the same id.
- Uses `HTTPException` to convert missing files into 404s and unexpected chat errors into 500s.
- `/api/chat` now treats `workspace_content` as transient turn context rather than silently persisting it before the reply, and it honors `workspace_scope` so hidden whiteboards do not silently ground ordinary chat. When the whiteboard is in scope, `ContextEngine` overlays the live buffer onto the loaded workspace document; when it is out of scope, `ContextSupport` blanks the workspace content before routing while keeping the active whiteboard id stable. The route delegates this lifecycle through `TurnOrchestrator`, which consumes a single `PreparedTurnContext`.
- `/api/chat` now delegates final turn-payload shaping to `turn_payloads.py`: `learned` stays canonical, `created_record` is backfilled as a thin compatibility alias, `graph_action.record_id` / `concept_id` stay mirrored, pending whiteboard `status` / `type` aliases are normalized both ways, and the pinned-context continuity surface is exposed explicitly as top-level `pinned_context` plus `pinned_context_id`, with `selected_record` / `selected_record_id` retained only as compatibility aliases. The same assembler-owned payload now also surfaces `turn_interpretation.whiteboard_entry_mode` so the UI can distinguish a fresh whiteboard start from continuing the current draft or reopening prior material.
- Local semantic-action and clarification helpers now live in `LocalSemanticActionEngine`, which creates `LocalTurnBodyParts` and returns `TurnResultParts` envelopes instead of final response dictionaries; `TurnOrchestrator` sends those parts through `assemble_local_turn_payload()` in `turn_payloads.py`, leaving `server.py` out of local action execution details.
- Saved concept, memory, artifact, and pinned-context payloads now add a thin lineage view-model on top of raw `comes_from`: `derived_from_id`, `revision_parent_id`, and `lineage_kind`. The server still stores lineage canonically in `comes_from`; these fields only help the UI tell generic provenance from concept-revision ancestry, and `record_cards.py` now prefers explicit `revision_of` metadata when it exists before falling back to legacy revision filename heuristics.
- Protocol concept payloads now expose a `kind="protocol"` view plus `protocol.protocol_kind`, `variables`, `applies_to`, `modifiable`, built-in, canonical, built-in-override, and canonical-override metadata. `ProtocolEngine` owns catalog listing, id/kind lookup, persisted override precedence, and API update write construction; `server.py` serializes those facts for `/api/protocols?include_builtins=true`, `GET /api/protocols/{protocol_kind_or_id}`, and `PUT /api/protocols/{protocol_kind}`.
- Final turn payloads now attach a safe `system_state` object plus a compact `activity` object. These expose session/surface/control availability, content-free workspace metadata, pinned/pending references, completed activity steps, graph actions, and created record ids without leaking hidden whiteboard content.
- Saved artifact payloads now also expose explicit lifecycle semantics through `DraftArtifactLifecycle` card enrichment: `artifact_origin` and `artifact_lifecycle` distinguish whiteboard snapshots, promoted artifacts, and Scenario Lab comparison hubs without changing the underlying storage truth that provenance still lives in `comes_from`.
- Whiteboard snapshot saves, visible-whiteboard publish actions, `/api/workspace` save snapshots, `/api/concepts/promote`, and `/api/concepts/open` saved-item reopen now delegate their storage/executor sequence to `DraftArtifactLifecycle`, keeping `server.py` responsible for HTTP routing and response serialization rather than lifecycle choreography.
- `/api/chat` resolves the pinned saved item, concept, memory, or vault note through `ContextSourceResolver` and asks the navigator service for a broader turn interpretation: whether the turn belongs in normal chat or Scenario Lab, whether the pinned context should stay anchored for continuity, and what whiteboard hint should guide normal chat. The navigator itself is now pinned-context-first; selected-record wording is only a compatibility layer at the server/client seam.
- Before that navigator call, `ContextSourceResolver` now also builds a small internal `continuity_context` view-model without changing the public `/api/chat` request shape. That continuity frame includes the current whiteboard summary, up to three recent whiteboards from the active runtime scope, an explicit `last_turn_referenced_record` when the latest Memory Trace wrote one, and a short `last_turn_recall` list reconstructed from the latest Memory Trace metadata. Older traces still fall back to preserved-context or unique-recall reconstruction. This keeps the interpreter continuity-aware for deictic follow-ups like `the other email` or `pull that up on the whiteboard` without flooding the model with a long whiteboard history.
- Pending whiteboard carry logic now lives in `WhiteboardRoutingEngine` and treats concise explicit phrases such as `open the whiteboard for ...` as connected to the prior offer, so response-mode disclosure can truthfully report `pending_whiteboard` or `mixed_context` when the original draft invitation is still active.
- Context-support workspace helpers now preserve or recompute `scenario_metadata` when a saved branch workspace is hidden for chat scope or overlaid with a live buffer, so the active workspace keeps its stable Scenario Lab identity even when the visible content changes or is blanked.
- `/api/chat` also normalizes an optional pending whiteboard-offer context from the previous turn through `ContextSupport`, but now only carries it forward when `WhiteboardRoutingEngine` accepts the current message: short acceptance phrases such as `let's do that` or `that works`, short continue/resume follow-ups that still reference the draft, short edit-follow-up turns, short deictic follow-up questions like `which one?` or `tell me more`, or only narrow explicit-whiteboard follow-ups that clearly point back to the prior draft/offer, including acceptance-prefixed forms like `okay, open the whiteboard` or `open it, put that in the whiteboard`. Fresh explicit whiteboard requests with substantive new content no longer carry stale pending whiteboard state. The routing engine also applies the same length bound as the client so long unrelated messages cannot silently keep carrying stale pending whiteboard state.
- `/api/chat` still writes turn traces under `traces/`, and it now also writes markdown-backed recent-history records under `memory_trace/` so Memory Trace remains distinct from the lower-level debug stream.
- That pending-whiteboard normalization now also backfills `workspace_update.status` from `type` and vice versa in `ContextSupport`, so older pending payloads keep working while `status` remains the canonical field.
- Ordinary `/api/chat` now drops pending whiteboard carry completely when the normalized pending payload does not include `origin_user_message`, which keeps the prompt context truthful and prevents `response_mode` from implying pending-whiteboard grounding when the original work-product request is unavailable.
- `/api/chat` can now also accept an unsaved `workspace_id` together with `workspace_content`; when the file does not exist yet and the whiteboard is in scope, the server builds a transient workspace document from the live buffer instead of failing, which lets the UI chat against a freshly forked whiteboard before the user saves it. If that unsaved workspace is out of scope, the server creates a placeholder document with empty content so normal chat still works instead of erroring.
- Saved artifact payloads, reopened workspaces, and pinned-context summaries now all keep `scenario_kind` visible and attach a nested `scenario` object when durable Scenario Lab metadata exists, including branch workspace ids plus the stable comparison branch index for comparison artifacts and namespace/base-workspace metadata for branch workspaces.
- That pinned-context summary lets the navigator keep follow-up questions anchored to an existing Scenario Lab artifact or other explicitly pinned item instead of re-running branch generation or dropping continuity.
- `/api/chat` deterministically merges explicit UI whiteboard choices with the navigator’s semantic whiteboard hint through `WhiteboardRoutingEngine` before it calls `ChatService.reply()`, so interpretation stays LLM-driven while policy and execution stay strict.
- `/api/chat` also includes a narrow deterministic override for explicit user phrasing like “open the whiteboard” or “draft this in the whiteboard”: when the navigator keeps the turn in normal chat, `WhiteboardRoutingEngine` upgrades auto-mode into `draft` immediately instead of asking for redundant confirmation.
- `/api/chat` now includes a second narrow whiteboard override for live drafting continuity: when the active whiteboard is already in scope with real content and the user is clearly revising that current draft, `WhiteboardRoutingEngine` upgrades an ambiguous or over-conservative offer hint into `draft` so Vantage updates the active whiteboard instead of reoffering a new one. That visible-draft matcher stays slightly broader than the pending-carry helper so greeting- or signature-level edits on the active whiteboard still continue the draft naturally.
- `/api/chat/whiteboard/accept` gives the UI a dedicated acceptance route for a pending whiteboard offer, so the client can confirm the collaboration flow without inventing a hidden user turn just to reach the draft path; the route replays the original work-product request from `pending_workspace_update.origin_user_message` so the draft is generated from the real prompt rather than from an opaque acceptance placeholder, and it intentionally bypasses the ordinary stale-carry guard because the acceptance route itself is explicit confirmation.
- `/api/chat` now returns a top-level `turn_interpretation` payload for both normal chat and Scenario Lab turns, giving the UI a compact explanation of the chosen path, requested and resolved whiteboard mode, the source of that whiteboard decision, pinned-context continuity, and the Navigator's `control_panel` plan without forcing it to infer those semantics from other fields.
- `/api/chat` also resolves Navigator `apply_protocol` actions into supported protocol kinds and passes them to normal chat or Scenario Lab, where deterministic services load the matching durable or built-in protocol into working memory before response generation.
- `/api/chat` also returns a sibling `semantic_frame` payload built from the already-resolved routing signals. This frame describes the likely user goal, task type, follow-up type, target surface, referenced object, confidence, inspectable signals, and product commitments without changing the underlying chat or Scenario Lab policy.
- `/api/chat` now derives a sibling `semantic_policy` payload from that frame plus known server context. For narrow command-like intents, the policy can act before generic chat: visible-whiteboard `save this` persists the whiteboard and creates a whiteboard snapshot artifact, visible-whiteboard `publish this artifact` promotes the current whiteboard into an artifact, ambiguous save/publish asks a clarification, and experiment-mode status/exit requests get a product-level local answer instead of going through the chat model.
- Scenario Lab turns still save branch workspaces plus a comparison artifact before the payload is returned, and Scenario Lab turns also write first-class Memory Trace records like normal chat.
- `/api/chat` serves the normal retrieval-vetting-response-meta pipeline when the navigator does not send the turn to Scenario Lab, and normal chat can now return non-destructive `workspace_update` metadata either to offer whiteboard collaboration for a work product or to propose a pending draft without mutating the workspace file. Pending draft proposals now use the canonical status `draft_ready`, which lets the frontend drop an older `pending -> draft_ready` translation layer.
- If Scenario Lab routing is chosen but the Scenario Lab service throws, `/api/chat` still recovers into normal chat, but the payload now includes an explicit `scenario_lab` failure object plus `scenario_lab_error` so the user-facing UI can explain that Scenario Lab failed after routing.
- `/api/chat` returns the service payload plus whiteboard scope and experiment metadata, now including `workspace.context_scope` so the client can inspect whether the whiteboard actually grounded the turn, and it backfills `workspace.content` when a transient in-scope whiteboard buffer was used even if the turn itself did not generate a new whiteboard proposal. Scenario Lab turns still carry the same truthful `response_mode` structure as normal chat, so the UI can tell when a comparison was grounded by whiteboard, recent-chat, or pending-whiteboard context instead of assuming every Scenario Lab turn is a best guess.
- `ChatService.reply()` now reports a more truthful grounding label for the answer surface: recall-grounded turns stay distinct from whiteboard-only, recent-chat-only, or pending-whiteboard turns, and the visible `This is new to me, but my best guess is:` preface is reserved for truly ungrounded replies.
- `POST /api/workspace` now honors an explicit `workspace_id` and makes that workspace active after saving, which lets accepted drafts become new first-class whiteboards instead of implicitly rewriting the previous active workspace; when that save targets an existing Scenario Lab branch and the edited content omitted the metadata block, the existing branch metadata is preserved so the branch identity survives the save. The route also auto-saves an artifact snapshot for that whiteboard iteration and returns both the workspace payload and the saved artifact metadata, including `artifact_origin="whiteboard"` and `artifact_lifecycle="whiteboard_snapshot"`.
- `/api/workspace/open` reopens an existing workspace branch by loading it from the active runtime store, switching the active workspace id to that branch, and returning the parsed stable scenario metadata from the workspace store; missing workspace ids now return a 404 instead of bubbling up as a generic server error.
- `/api/concepts/promote` can promote either a saved workspace or an unsaved whiteboard draft buffer into an artifact. When `workspace_id` does not exist on disk yet but `content` is provided, the route now builds a transient `WorkspaceDocument` from that buffer instead of failing or implicitly saving a new workspace file first; when a saved workspace exists, it overlays the submitted content in memory before promotion rather than persisting the workspace as a side effect. Promoted payloads now carry `artifact_origin="whiteboard"` and `artifact_lifecycle="promoted_artifact"` so the UI can describe them truthfully without inferring promotion from the route alone.
- `/api/concepts/open` accepts `record_id` as the generic saved-item alias, keeps `concept_id` for compatibility, and delegates the selected-item reopen flow to `DraftArtifactLifecycle`. Its `graph_action` now truthfully uses the generic `open_saved_item_into_workspace` label while still mirroring `concept_id` for older clients; missing saved items are normalized into a clean 404, and protocol records are rejected as 400s because protocols are guidance/editing objects rather than whiteboard drafts.
