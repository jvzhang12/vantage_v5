# Vantage Current Architecture

This is the quickest architecture map for agents working in the current repository.

Read this after [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md) and before editing implementation files.

## Product Shape

Vantage is a chat-first local web app with three major product surfaces:

- `Chat`: the default interaction surface.
- `Whiteboard`: an on-demand Markdown drafting surface backed by the `workspaces/` storage implementation.
- `Vantage`: the inspection surface for what was understood, what was in scope, what was recalled, what was learned, and Scenario Lab outputs.

The implementation still uses `workspace_*` names in API payloads and storage paths. Product copy and new docs should say `Whiteboard` unless they are naming a compatibility field or concrete source file.

The current Vantage surface intentionally hides the full Library dock while keeping the DOM and data-loading paths available for future restoration. Saved concepts, memories, artifacts, and reference notes still exist and can appear through Recall, learned-item cards, inspectors, or reopen flows.

## Runtime Request Path

The normal `/api/chat` path is:

1. Browser sends the user message, recent chat, optional pinned context, whiteboard scope, live whiteboard buffer, and pending whiteboard offer/draft state.
2. `server.py` builds the app/runtime seams, then delegates chat-turn execution to `TurnOrchestrator`.
3. `ContextEngine` prepares a single `PreparedTurnContext`: durable or experiment runtime, scoped whiteboard document, pinned context, pending whiteboard carry state, whiteboard entry mode, and Navigator continuity frame.
4. `TurnOrchestrator` calls `NavigatorService` to interpret the turn with recent chat, current whiteboard excerpt, pinned context, pending whiteboard state, and the continuity frame.
5. The Navigator returns `NavigationDecision`, including route hints and a `control_panel` plan.
6. `ProtocolEngine` validates Navigator `apply_protocol` controls into a typed `ResolvedTurnProtocols` object and builds protocol guidance candidates with persisted override precedence plus built-in fallback.
7. `TurnOrchestrator` resolves strict execution policy: whiteboard mode, applied protocol kinds, semantic frame, semantic policy, local save/publish/experiment actions, or Scenario Lab routing.
8. Normal chat calls `ChatService.reply()`. Scenario turns call `ScenarioLabService.run()`.
9. The chosen service performs bounded retrieval, protocol injection when requested, vetting, model response or scenario generation, conservative graph writes, and Memory Trace creation.
10. `turn_payloads.py` finalizes response compatibility, `turn_interpretation`, whiteboard scope disclosure, safe state, and activity while `TurnOrchestrator` supplies the typed parts needed for assembly.
11. The browser normalizes payloads in `turn_payloads.mjs` and renders chat evidence, Inspect/Vantage state, whiteboard proposals, and Scenario Lab review.

## LLM Interpretation vs Deterministic Execution

The target architecture is LLM-directed interpretation with deterministic execution.

The Navigator LLM should decide user intent and return structured actions in `control_panel`. Deterministic code should validate and execute those actions, not infer broad user intent from raw text.

Current implemented control-panel actions include:

- `respond`
- `recall`
- `apply_protocol`
- `open_whiteboard`
- `draft_whiteboard`
- `open_scenario_lab`
- `inspect_context`
- `save_whiteboard`
- `publish_artifact`
- `close_surface`
- `preserve_surface`
- `manage_experiment`
- `ask_clarification`

Some deterministic raw-text helpers still exist as transitional guardrails, especially in semantic frame/policy handling, whiteboard carry logic, meta fallback, and client-side deictic reopen. Treat those as migration targets, not the desired long-term architecture. See [control-panel-navigation.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/control-panel-navigation.md).

Deterministic fallback is allowed only when it stays narrow, conservative, and visible. It may repair or validate a missing structured field, protect a safety boundary, keep the app responsive when the model/provider is unavailable, or preserve compatibility with older payloads. It must not become a silent semantic crutch.

When fallback affects behavior, traces or payload metadata should label it explicitly, for example `compiler.source="deterministic_fallback"` or a similarly clear authority/provenance field. Fallback must not masquerade as Navigator, model, or control-panel authority. If a normal product prompt requires broad raw-text fallback to pass, the preferred fix is to expose and repair the missing LLM-mediated structured intent.

## Working Memory And Recall

Product `Working Memory` means the full bounded context used for generation: current user request, recent chat, recalled items, pinned context, whiteboard context when in scope, and pending whiteboard context when intentionally carried forward.

`Attention` is the broad turn selection mechanism across saved memory, visible surfaces, app resources, protocols, openable artifacts, and other resources. `Recall` is the memory-grounding role/view over selected Attention resources.

API `recall` is currently narrower: the vetted retrieved subset from Memory Trace and Library sources. Legacy `working_memory` is still emitted as an alias for that recalled subset, not the full product concept. `ChatService.search_context()` remains a transitional independent retrieval path; final-response traces include an internal Attention/Recall context handoff that compares selected Attention resources with legacy Recall output but does not change prompt context or generation. The trace-only Attention/Recall role projection and public Working Memory view are now built from that handoff so they share one compact role/provenance source.

The latest-turn `/api/chat` response also includes `working_memory_view`, a bounded product-safe contract consumed by the React Vantage Working Memory UI. It groups compact resources by `answer_context`, `recall_context`, `protocol_guidance`, `surface_to_open`, and `pinned_or_continuity_context`, then adds a compact execution summary from TurnPlan surface actions and write/proposal ledger categories. This payload exposes grounding/context/provenance and finalized UI/write decisions; it does not expose hidden chain-of-thought, raw prompts, or full artifact/memory/concept/protocol bodies.

Protocol candidates can be injected into the candidate memory set before vetting. That is how non-obvious but relevant reasoning guidance, such as Scenario Lab first-principles/counterfactual reasoning, can reach the model without brittle semantic search.

Turn responses now also include a safe `system_state` payload and a compact final `activity` payload. The former exposes product state such as available surfaces, available controls, experiment status, draft metadata, and selected/pinned references without hidden draft content. The latter gives the UI completed steps and actions for a quiet activity/provenance line without requiring streaming.

The deep-module refactor moved context preparation into `services/context_engine.py`, protocol action resolution into `services/protocol_engine.py`, draft/artifact lifecycle operations into `services/draft_artifact_lifecycle.py`, record-card presentation into `services/record_cards.py`, and turn payload construction/final backend response shaping into `services/turn_payloads.py`, so context safety, protocol validation, artifact lifecycle semantics, UI-facing record DTOs, safe state, and activity are owned by explicit module boundaries rather than by the HTTP route.

## Protocols

Protocols are reusable instructions for recurring work types.

Current protocol kinds:

- `email`
- `research_paper`
- `scenario_lab`

There are two paths into protocol use:

- `ProtocolEngine` can run `ProtocolInterpreter` and apply its structured decision when a turn updates or recalls a durable protocol.
- The Navigator can press `apply_protocol` with a `protocol_kind`, and deterministic code can inject a durable or built-in protocol into working memory.

The built-in `scenario_lab` protocol is a reasoning recipe. It should be treated as task guidance, not a factual source.

Protocols are now editable through Inspect. `GET /api/protocols?include_builtins=true` can surface built-ins, `GET /api/protocols/{protocol_kind_or_id}` resolves by kind or id, and `PUT /api/protocols/{protocol_kind}` writes a durable or experiment-scoped protocol record. Editing a built-in or canonical default creates a persisted user/session override rather than mutating the shipped default.

`protocol_engine.py` is the turn-time resolution seam. It consumes Navigator `apply_protocol` controls, validates supported protocol kinds, deduplicates actions, returns `ResolvedTurnProtocols`, applies interpreter-driven protocol learning/upserts, and builds `ProtocolGuidance` candidate memory for Chat or Scenario Lab. User/session protocol records take precedence over canonical defaults, and canonical or persisted records take precedence over built-ins; built-ins such as Scenario Lab remain available as advisory reasoning recipes when no override exists.

## Semantic Frame And Policy

`semantic_frame.py` builds a product-facing read model of what Vantage understood: user goal, task type, follow-up type, target surface, referenced object, signals, commitments, and confidence.

`semantic_policy.py` consumes that frame plus server-known facts and decides narrow local behavior. It currently handles:

- visible-whiteboard save
- visible-whiteboard publish
- ambiguous save/publish clarification
- experiment-mode status and exit behavior

This layer is deterministic by design for local safety, but it should not become a broad replacement for Navigator intent interpretation. As control-panel coverage expands, more of this should be driven by Navigator actions and deterministic validation.

Whiteboard draft/offer authority now follows the same boundary. Navigator, control-panel, composer mode, or existing Whiteboard routing provide structured draft/offer intent; TurnPlan validates that authority before a pending `workspace_update` draft or offer can be materialized. Hard no-write surface actions such as open-only, close, preserve, and ordinary visible-artifact Q&A block draft/offer candidates and force honest receipts instead of allowing draft snapshots or misleading offer copy.

When semantic policy chooses a visible-whiteboard save or publish action, `draft_artifact_lifecycle.py` executes the storage lifecycle. The policy decides whether a local action is allowed; the lifecycle service owns how whiteboards become snapshots or promoted artifacts.

## Near-Term Architecture Direction

The old implementation roadmap is archived. Active implementation direction should come from the current product docs, this architecture overview, codebase maps, and the live lane handoff.

The next backend cleanup is TurnPlan execution consolidation. The goal is to reduce duplicated authority paths across `TurnOrchestrator`, `ChatService`, `server.py`, local semantic actions, draft/offer handling, protocol/meta execution, and artifact-action compilation. TurnPlan should compute authority; orchestrator should dispatch; downstream services should consume explicit allow/deny policy and serialize/project safe outputs rather than recomputing broad semantic gates.

The React frontend now begins visible-surface state separation. The reducer keeps `view`, `visibleSurfaces`, `whiteboardEditor`, `selectedResource`, `pinnedContext`, and included request context as separate facts, while compatibility props still feed existing components. Responsive layout state remains a later cleanup.

## Scenario Lab

Scenario Lab is a distinct route for comparative what-if and option-analysis work.

It writes:

- branch workspaces under `workspaces/`
- a durable comparison artifact under `artifacts/`
- a Memory Trace record for the turn

Follow-up questions on existing scenario comparisons should usually stay in chat with pinned-context continuity unless the user explicitly asks for new branches, a rerun, or a new comparison set.

## Storage Model

The repository is currently a Markdown-backed local product database:

- `canonical/`: shipped Vantage defaults, read underneath user/session stores and not mutated by user edits.
- `concepts/`: timeless knowledge and protocols.
- `memories/`: retained continuity facts.
- `artifacts/`: concrete work products, whiteboard snapshots, promoted artifacts, and Scenario Lab comparison hubs.
- `workspaces/`: whiteboard documents and Scenario Lab branch workspaces.
- `memory_trace/`: markdown-backed recent-history records used for recall.
- `traces/`: JSON debug traces.
- `state/`: active whiteboard/workspace and experiment state.
- `users/<username>/`: isolated profile stores when multi-user Basic Auth mode is enabled.

Experiment mode swaps the writable stores to session-local directories while durable stores remain readable reference context. Canonical defaults remain the lowest-priority read-through layer in both durable and experiment modes, so a user can override a default without changing it for other profiles.

## Frontend Architecture

The active browser app is the React frontend under `src/vantage_v5/webapp_react/`.

- `index.html` provides the Vite development shell and `#root` mount point.
- `src/main.tsx` mounts the React `App` and registers the root service worker when the browser context is secure.
- `src/App.tsx` owns the top-level browser workflow and delegates surface rendering, request shaping, and state transitions to typed React modules.
- `src/appReducer.ts`: explicit chat, Whiteboard, Vantage, visible-surface, selected-resource, pinned-context, and request-context state.
- `src/normalizers.ts`: backend DTO normalization for the React state model.
- `src/visibleArtifacts.ts`: visible-surface and Whiteboard context serialization for chat requests.
- `src/components/`: React presentation components for core shell, inspection, artifact surfaces, and product mark.

`npm run build` emits the production bundle into `src/vantage_v5/webapp/generated/` with public URLs under `/static/generated/`. FastAPI serves that generated React `index.html` at `/` when it exists, while root PWA asset routes prefer generated files and fall back to `src/vantage_v5/webapp_react/public/`.

The older vanilla files under `src/vantage_v5/webapp/` remain present as a server fallback when no generated React build exists and as direct fixtures for some legacy helper tests. They should not be treated as the active frontend entrypoint without first removing or replacing those fallback and test dependencies.

The UI is intentionally not a control panel for every internal subsystem. Chat stays primary, Whiteboard is for drafting, and Vantage is for guided inspection.

## Deployment Shape

Local development binds to `127.0.0.1` by default. Hosted/private access should configure:

- `VANTAGE_V5_HOST=0.0.0.0` only behind a private network, tunnel, or reverse proxy.
- `VANTAGE_V5_AUTH_PASSWORD` for single-user Basic Auth, or `VANTAGE_V5_AUTH_USERS_JSON` / `VANTAGE_V5_AUTH_USERS_FILE` for isolated user profiles.
- `VANTAGE_V5_REPO_ROOT=/data` in Docker with a persistent volume.

See [deployment.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/deployment.md).

## Source Maps For Agents

Use [codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md) before editing. Each source/test file should have a mirrored summary under `docs/codebase/`.

When a source or test file changes, update its mirrored summary in the same patch and run:

```bash
python3 scripts/check_repo_hygiene.py
```
