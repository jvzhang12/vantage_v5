# Vantage Codebase Functionality Map

> Status: Historical rationale
> Current source of truth: [docs/architecture-overview.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/architecture-overview.md) and [docs/codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md)
> Note: This generated read-only assessment is preserved for context. It was produced from a dirty worktree and should not be treated as current implementation guidance when it differs from the current codebase maps or architecture overview.

Generated: 2026-05-09

Repository: `/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5`

Purpose: establish a shared, code-backed view of what Vantage currently does so future OpenClaw comparison work can start from a grounded map instead of vibes.

Notes:
- This is a synthesis of direct code inspection plus six scoped sub-agent read-only assessments.
- The worktree was dirty during assessment, so this reflects the files as they existed at inspection time.
- The test suite was not run as part of this mapping pass.

## Executive Shape

Vantage is a local-first LLM workbench whose default product experience is chat. It quietly maintains inspectable memory and context behind the scenes, and it can open a drafting surface when the conversation turns into a concrete work product.

The major product surfaces are:

- `Chat`: the primary user surface.
- `Whiteboard` / `Draft`: the live drafting surface for work products.
- `Inspect` / `Vantage`: the answer-context and audit surface.
- `Library`: durable saved concepts, memories, artifacts, protocols, and reference notes. Some UI paths exist but the main library dock is currently hidden.
- `Scenario Lab`: a branch-and-compare workflow for generating alternatives and comparison artifacts.
- `Experiment Mode`: isolated temporary stores for test runs.

The main runtime path is:

```text
Browser app
  -> POST /api/chat
  -> TurnOrchestrator
  -> ContextEngine
  -> NavigatorService
  -> WhiteboardRoutingEngine
  -> ProtocolEngine
  -> SemanticFrame + SemanticPolicy
  -> LocalSemanticActionEngine or ScenarioLabService or ChatService
  -> finalize_turn_payload()
  -> frontend normalizeTurnPayload()
  -> Chat / Draft / Inspect rendering
```

The most important architectural idea is that Vantage separates "what the assistant saw" from "what it saved." Retrieval produces candidates, vetting selects a small set for the current answer, every turn leaves a Memory Trace, and only explicit or meta-approved writes become durable records.

## Source Coverage

The assessment was split across these domains:

- Backend/API: `server.py`, config, routes, app composition, auth, runtime store selection.
- Memory/recall: markdown stores, Memory Trace, search, vetting, response grounding, corrections.
- Turn orchestration: context preparation, routing, semantic policy, whiteboard continuation, staged output.
- Frontend/Inspect: React source under `src/vantage_v5/webapp_react`, generated bundle serving under `src/vantage_v5/webapp/generated`, turn payload normalization, surface state, product copy.
- Scenario/protocol/artifact lifecycle: Scenario Lab, protocol engine, experiment stores, draft artifacts.
- Tests/contracts: documented behavior promises, payload compatibility, routing invariants, gaps.

Primary source paths:

- `src/vantage_v5/server.py`
- `src/vantage_v5/services/turn_orchestrator.py`
- `src/vantage_v5/services/context_engine.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/search.py`
- `src/vantage_v5/services/vetting.py`
- `src/vantage_v5/services/navigator.py`
- `src/vantage_v5/services/whiteboard_routing.py`
- `src/vantage_v5/services/semantic_frame.py`
- `src/vantage_v5/services/semantic_policy.py`
- `src/vantage_v5/services/local_semantic_actions.py`
- `src/vantage_v5/services/turn_payloads.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/services/protocol_engine.py`
- `src/vantage_v5/services/protocols.py`
- `src/vantage_v5/services/draft_artifact_lifecycle.py`
- `src/vantage_v5/storage/*.py`
- `src/vantage_v5/webapp_react/src/App.tsx`
- `src/vantage_v5/webapp_react/src/*.ts`
- `src/vantage_v5/webapp_react/src/components/*.tsx`
- `tests/*.py`
- React/Vitest frontend tests under `src/vantage_v5/webapp_react/src/*.test.ts*`

## Product Surface Map

| Surface | What It Does | Important Files | Current Assessment |
|---|---|---|---|
| Chat | Primary interaction mode. Sends message, history, selected context, whiteboard scope, pinned context, and pending draft updates to `/api/chat`. | React `webapp_react/src/App.tsx` / `appReducer.ts` / `visibleArtifacts.ts`, `server.py`, `chat.py` | Mature and central. Chat remains the default even when memory and protocols are active. |
| Whiteboard / Draft | Live markdown workspace for longer work products. Can be offered, accepted, drafted, saved, published, or reopened from saved records. | React `webapp_react/src/App.tsx` / `appReducer.ts`, `context_engine.py`, `whiteboard_routing.py`, `draft_artifact_lifecycle.py`, `workspaces.py` | Strong user-facing draft model. Pending-offer carry is deliberately narrow. Draft retention and expiry are still TODO-level. |
| Inspect / Vantage | Shows answer context, pulled-in memory, saved items, Memory Trace, reasoning path, Scenario Lab state, correction affordances, and product-facing grounding labels. | React `webapp_react/src/components/Inspection.tsx` / `normalizers.ts`, `turn_payloads.py` | One of Vantage's strongest differentiators. It makes the context loop legible. Real browser/DOM integration coverage appears thinner than model-level tests. |
| Library | Durable saved layer: concepts, memories, artifacts, protocols, vault notes. Some library dock UI exists but is hidden by a feature flag. | React shell state, `markdown_store.py`, `concepts.py`, `memories.py`, `artifacts.py`, `vault.py`, `record_cards.py` | The storage model is clear and inspectable. The product surface is less prominent than the underlying capability. |
| Scenario Lab | Generates 2-3 branches, writes branch workspaces, creates a comparison artifact, and records a scenario turn trace. | React shell state, `scenario_lab.py`, `workspaces.py`, `artifacts.py`, `record_cards.py` | Substantial and well-integrated, but model-dependent and only lightly semantically validated before durable writes. |
| Experiment Mode | Starts isolated temporary stores under `state/experiments`, overlays durable/canonical references, deletes the session on end. | `experiments.py`, `server.py` | Clean isolation. Missing a first-class "promote useful experiment outputs to durable" path before deletion. |

## Backend/API Map

Backend entrypoints:

- Package script: `vantage-v5-web = "vantage_v5.server:main"` in `pyproject.toml`.
- App factory: `create_app(config)` in `server.py`.
- Static app: `/static` serves generated React assets from `src/vantage_v5/webapp`; `/` returns `src/vantage_v5/webapp/generated/index.html` when the generated React build exists and otherwise returns a clear build-required setup error. Root PWA routes prefer generated files and fall back to `src/vantage_v5/webapp_react/public`.
- Docker runtime creates `/data/{artifacts,concepts,memories,memory_trace,state,traces,users,workspaces}`.

Major route families:

- Health/auth/key management: `/api/health`, `/api/login`, `/api/accounts`, `/api/logout`, `/api/openai-key`.
- Experiment mode: `/api/experiment/start`, `/api/experiment/end`.
- Workspace/whiteboard: `/api/workspace`, `/api/workspace/open`, `/api/chat/whiteboard/accept`.
- Library/catalog: `/api/concepts`, `/api/memory`, `/api/vault-notes`, item lookup routes.
- Protocols: `/api/protocols`, `/api/protocols/{kind_or_id}`, `PUT /api/protocols/{kind}`.
- Search/corrections: concept, memory, vault search routes plus `/api/records/{source}/{record_id}/corrections`.
- Chat: `POST /api/chat`.

Backend strengths:

- FastAPI app is straightforward to run and inspect.
- Local-first state is easy to reason about on disk.
- Runtime selection cleanly separates durable mode from experiment mode.
- Most important turn logic is now factored into services rather than buried only in routes.

Backend risks:

- `server.py` is still a large composition root plus router plus auth/session manager plus API schema holder.
- Most responses are plain dictionaries, so OpenAPI/schema validation is weak relative to payload complexity.
- Sessions and per-user OpenAI keys are in-memory dictionaries, not durable or multi-process safe.
- File-backed writes are simple but do not visibly use locks or transactions.
- Product/API vocabulary still mixes `workspace` with the newer product term `Whiteboard`.

## Storage And Memory Model

Vantage's storage model is intentionally inspectable and mostly markdown-backed.

Durable root folders:

- `concepts/`
- `memories/`
- `memory_trace/`
- `artifacts/`
- `workspaces/`
- `state/`
- `traces/`

Multi-user mode stores the same structure under `users/<safe_user_id>/`. Canonical defaults live under `canonical/` and can be read as references. Experiment mode creates temporary scoped copies under `state/experiments/<session_id>/`.

Record types:

- Concepts: high-trust durable knowledge records.
- Memories: medium-trust saved user preferences or explicit memories.
- Artifacts: saved work products, snapshots, promoted drafts, scenario comparisons.
- Memory Trace: searchable recent turn history.
- Vault notes: read-only external markdown notes from configured Nexus/Obsidian paths.
- Protocols: stored as concept records with protocol metadata.
- Workspaces: plain markdown documents representing active whiteboards and Scenario Lab branches.

Search and recall:

- `search_context()` merges Memory Trace, concepts, saved notes, and vault notes into `CandidateMemory` items.
- Retrieval is lexical/token-overlap based with hand weights, source bonuses, phrase bonuses, and memory-trace recency/continuity boosts.
- The candidate pool is intentionally bounded, commonly around 16 items.
- `VettingService` selects up to 5 focused items for the actual generation context.
- Pinned or selected records can be preserved through low-context follow-ups.

Grounding:

- `response_mode.py` categorizes answers as `recall`, `whiteboard`, `recent_chat`, `pending_whiteboard`, `mixed_context`, or `ungrounded`.
- `answer_basis` separates factual evidence from protocol guidance.
- Protocols guide the answer but are not counted as factual grounding.
- Context Budget is a human-readable inclusion receipt, not real token accounting.

Memory strengths:

- Strong source taxonomy: concept, protocol, memory, artifact, vault note, and memory trace carry different roles and trust cues.
- Memory Trace gives continuity without promoting every turn into durable knowledge.
- Corrections hide/suppress records rather than destroying them.
- Experiment writes are isolated and easy to delete.

Memory gaps:

- Retrieval is lexical, not semantic/vector based.
- No chunk index, embedding store, learned ranker, or citation-level retrieval.
- Grounding is presence-based rather than claim-verified.
- Vault integration is shallow: no Obsidian wikilink graph, backlink traversal, or section-level chunking.
- Corrections do not support direct edits, confidence/freshness labels, "make temporary," or trace/vault-note correction.
- Memory Trace has recency limits but no clear retention, pruning, or compression policy.

## Turn Lifecycle

A normal turn works roughly like this:

1. Frontend builds a chat request from message, history, whiteboard visibility/content, selected record, pinned context, memory intent, and pending workspace update.
2. `POST /api/chat` receives a `ChatRequest`.
3. `_chat_turn_response()` constructs a runtime and `TurnOrchestrator`.
4. `ContextEngine.prepare_turn_context()` resolves active workspace, scope, hidden/live buffers, pinned context, selected record, pending update, experiment state, and navigator continuity context.
5. `NavigatorService` decides route, whiteboard mode, pinned-context preservation, and control-panel actions.
6. `WhiteboardRoutingEngine` stabilizes whiteboard behavior using explicit UI mode, active draft state, pending offers, and navigator hints.
7. `ProtocolEngine` resolves applied protocols from navigator actions, deterministic task detection, stored overrides, or built-ins.
8. `semantic_frame.py` and `semantic_policy.py` derive deterministic goal/task/surface/action state.
9. `LocalSemanticActionEngine` can short-circuit generic chat for clarification, save, publish, and experiment status.
10. Otherwise, the orchestrator runs either `ScenarioLabService` or `ChatService`.
11. Chat retrieval gathers candidates, vetting selects relevant context, OpenAI or fallback generation runs, whiteboard labels are parsed, meta writes execute, and Memory Trace is written.
12. `turn_payloads.py` normalizes the response for the frontend.
13. The React frontend normalizes snake/camel/legacy payload shapes through `normalizers.ts` and renders Chat, Whiteboard, Vantage, and Scenario Lab surfaces.

Strong invariants from tests/docs:

- Default UX is chat-first.
- Whiteboard content is excluded when hidden unless explicitly visible, requested, or pinned.
- Pending whiteboard carry is deliberately narrow.
- UI-requested chat wins over whiteboard phrasing.
- Requested offer/draft wins over navigator hints.
- Scenario Lab is distinct from Whiteboard drafting.
- Every chat/scenario turn should write a Memory Trace.
- `recall` is the canonical selected subset; `working_memory` remains a compatibility alias.

## Routing, Semantics, And Policies

Vantage has three layers of intent handling:

- Model-led navigation: `NavigatorService` chooses high-level mode and control-panel actions when OpenAI is configured.
- Deterministic stabilization: Python and JS code override or bound fragile decisions, especially around whiteboard behavior, email drafts, and explicit UI modes.
- Semantic policy: a local deterministic layer recognizes save, publish, experiment management, context inspection, and clarification cases.

Strengths:

- The assistant is less likely to surprise the user because UI intent and deterministic gates can overrule ambiguous model output.
- Whiteboard offer/draft behavior is represented on both client and server.
- Staged output and public activity payloads sanitize provider/debug details before display.

Risks:

- Routing regexes exist in multiple places across Python and JavaScript, so drift is likely.
- `semantic_policy` can produce context-inspection intent, but local action handling is narrower than the policy vocabulary.
- Publish confirmation may be broad when a referenced object and workspace content are both in scope.
- The stricter stage audit exists, but the primary chat path mostly checks that required offer/draft surfaces exist rather than deeply validating structured content.

## Whiteboard, Artifacts, And Draft Lifecycle

Whiteboard behaviors:

- Offer: chat proposes opening a draft surface. It does not persist.
- Draft: chat creates a `workspace_update` and may auto-create an artifact snapshot for inspection.
- Save: persists the workspace and creates a `whiteboard_snapshot` artifact.
- Publish/promote: creates a promoted artifact, sometimes using an unsaved buffer without persisting the workspace first.
- Reopen: wraps a saved concept, memory, or artifact body into a workspace. Protocol records are rejected.

Strengths:

- Clear distinction between ephemeral draft, saved snapshot, promoted artifact, and scenario comparison.
- Hidden draft content is protected unless the user explicitly brings it into scope.
- Draft/artifact lifecycle logic is centralized in `DraftArtifactLifecycle`.

Gaps:

- Draft retention/expiry is documented as TODO-level work.
- Draft-mode chat can create snapshot artifacts even while `workspace_update.persisted` is false, which may surprise users or clutter durable state.
- APIs still use names like `/api/concepts/promote` and `/api/concepts/open` for broader saved-item flows.

## Scenario Lab

Scenario Lab is a separate route for branch/comparison generation. It is entered when the navigator chooses `scenario_lab` with sufficient confidence. It:

- Reuses retrieval and vetting.
- Applies Scenario Lab protocol guidance.
- Builds a structured model-backed plan with shared assumptions, 2-3 branches, tradeoffs, recommendation, and next steps.
- Writes branch workspaces.
- Writes a comparison artifact.
- Writes a Memory Trace.
- Renders a dedicated Inspect dock with branch and comparison state.

Strengths:

- Scenario metadata is duplicated across markdown body, frontmatter, artifact parsing, and UI cards.
- Branch workspaces and comparison artifacts are first-class saved objects.
- Experiment mode can isolate scenario runs.

Risks:

- Scenario generation is model-dependent and only lightly validated.
- Weak branch details can be padded by defaults and still persisted.
- Namespace selection uses token overlap and title heuristics.
- Writes are not transactionally grouped; partial state is possible on edge failures.
- Ending an experiment deletes the session root, and there is no obvious promote-before-delete workflow.

## Protocols

Vantage supports protocol guidance for repeatable task styles.

Supported kinds observed:

- `email`
- `research_paper`
- `scenario_lab`

Protocol facts:

- Protocols are stored as concept records with `type=protocol`.
- Protocol application can come from navigator actions or deterministic task-surface detection.
- Persisted/custom protocol records override built-in guidance when available.
- Protocol updates can be inferred, but write permission is gated by reusable-preference intent.
- Protocols appear in Inspect as guidance, not factual evidence.

Strengths:

- Good fit for personal style preferences and repeatable workflows.
- Clean separation from factual grounding through `answer_basis`.
- User/session protocol overrides are possible without changing code.

Risks:

- Protocol write gating is regex-based after model interpretation and may reject valid phrasing.
- Protocol interpretation swallows exceptions and returns no action, which is safe but weak for debugging.
- Only Scenario Lab appears to be hard-coded as a built-in protocol in code; email/research behavior is more detection/guidance dependent.

## Frontend And Inspect

Frontend structure:

- The active browser app is the React source under `src/vantage_v5/webapp_react`.
- `npm run build` writes the generated React browser shell under ignored `src/vantage_v5/webapp/generated/`, and FastAPI serves that generated shell at `/`.
- If the generated React index is missing, FastAPI returns a clear build-required setup error; there is no legacy product frontend fallback.
- `src/vantage_v5/webapp_react/src/App.tsx` owns the top-level browser workflow.
- `src/vantage_v5/webapp_react/src/appReducer.ts`, `normalizers.ts`, and `visibleArtifacts.ts` carry the typed state, backend DTO, and visible-context contracts.
- `src/vantage_v5/webapp_react/src/components/` contains the core shell, inspection, and surface presentation components.
- The older committed vanilla `src/vantage_v5/webapp/index.html`, `app.js`, `styles.css`, helper modules, and vendor files have been removed. The remaining `src/vantage_v5/webapp/generated/` path is ignored build output.

Inspect renders:

- Answer Context.
- Context in Scope.
- Pulled In.
- Saved for Later.
- Details.
- Memory Trace.
- Reasoning Path.
- Scenario Lab.
- Correction panels.

Strengths:

- UI vocabulary is product-facing rather than provider/debug-facing.
- Inspect is deeply integrated with recall, trace, answer basis, protocols, and Scenario Lab.
- Compatibility normalization is broad, which helps evolve backend payloads without breaking the UI.

Risks:

- Frontend and backend duplicate normalization concepts, especially context budget, response mode, and workspace updates.
- True browser/DOM integration coverage appears limited compared with pure state/model tests.
- The Library dock is hidden behind `SHOW_LIBRARY_DOCK = false`, leaving semi-dead UI paths.

## Tests And Behavior Contracts

The test suite encodes many product promises:

- Search returns mixed candidates and vetting narrows to a small working set.
- Chat responses preserve `recall` and legacy `working_memory`.
- Context Budget is a scope receipt, not token accounting.
- Hidden whiteboard content is excluded unless explicitly in scope.
- Pending whiteboard carry is narrow.
- Whiteboard offers do not persist.
- Draft requests do not auto-write concepts/memories.
- Explicit "remember" can create memory.
- Explicit save/publish creates artifact flows.
- Scenario Lab creates branch workspaces and comparison artifacts.
- Experiment mode isolates writes.
- Corrections are hide/suppress semantics, not hard deletes.
- Product identity labels distinguish evidence from guidance.

Coverage appears strong around backend behavior and frontend pure state models. The thinner area is likely end-to-end browser rendering and interaction coverage for Inspect, surface switching, layout regressions, and real DOM behavior.

## Time And Operational State

Vantage has timestamps, but not a first-class time system.

What exists:

- Markdown records have `created_at` / `updated_at`.
- Memory Trace records are recent-list sorted.
- Vault notes have modified-time metadata.
- Scenario and artifact records carry lifecycle metadata.
- Some docs mention future draft retention and expiry concepts.

What does not appear to exist yet:

- `due_at`, `scheduled_at`, `starts_at`, `expires_at`, or recurrence fields as shared semantics.
- A reminder/follow-up/commitment store.
- A task ledger.
- A scheduler, heartbeat, daemon, or wakeup loop.
- A background queue.
- A notion of time-sensitive retrieval beyond recency weighting.
- A model for "I promised to do/check this later."
- UI affordances for upcoming, overdue, completed, or snoozed commitments.

This matters for OpenClaw comparison because any OpenClaw functionality around follow-ups, tasks, scheduler state, reminders, or temporal commitments would fill a real gap in Vantage rather than duplicate an existing mature system.

## Strengths To Preserve

- Chat-first feel with optional heavier surfaces.
- Local-first markdown state that can be inspected and versioned.
- Clear distinction between candidate memory, vetted recall, durable memory, and Memory Trace.
- Strong Inspect story for answer context and auditability.
- Deterministic safeguards around whiteboard scope and user intent.
- Protocol guidance is separated from factual evidence.
- Scenario Lab is already a serious branch/comparison system.
- Experiment mode gives a safe place to test without polluting durable user memory.

## Main Weaknesses And Merge Opportunities

Highest-leverage gaps:

1. First-class time and commitments
   - Vantage has recency metadata but not operational temporal state.
   - A small temporal substrate would unlock reminders, follow-ups, draft expiry, task promises, and scheduled checks.

2. Durable conversation resume
   - Visible transcript/history is still effectively client-driven and session-scoped.
   - Memory Trace helps continuity, but it is not a full conversation transcript/resume system.

3. Semantic retrieval
   - Current recall is lexical and bounded.
   - Embeddings, chunking, link graph traversal, or learned reranking would improve recall quality.

4. Claim-level grounding
   - Vantage knows which sources were present, but does not validate individual claims against citations.

5. Cleaner schema boundaries
   - Complex response dictionaries and duplicated JS/Python normalization create drift risk.
   - Pydantic response models or shared schema generation would help.

6. Operational write safety
   - Scenario and markdown writes are file-based without obvious locks or transactions.
   - Multi-session or multi-worker behavior may become fragile.

7. Frontend modularity
   - `app.js` carries too much.
   - Inspect, catalog, chat request composition, correction flows, and render state could gradually split into smaller modules.

8. Experiment promotion
   - Experiment mode can isolate and delete work, but lacks a clear "promote this useful result" path.

9. Library product surface
   - The storage layer is strong, but the visible Library affordance is subdued or hidden.

10. Connector/plugin/task ecosystem
   - Vantage does not appear to have a general plugin/connector/action registry beyond its internal route/service structure.

## OpenClaw Merge Radar

This file is not a full OpenClaw comparison, but it suggests what to look for when mapping OpenClaw:

- Does OpenClaw have a task/commitment ledger?
- Does OpenClaw encode time with due dates, reminders, recurrence, expiry, or scheduling?
- Does OpenClaw have a heartbeat/worker loop or background job model?
- Does OpenClaw model promises separately from memories?
- Does OpenClaw have stronger tool/plugin/connector registration?
- Does OpenClaw support multi-agent or delegated work as a first-class workflow?
- Does OpenClaw have stronger conversation/session resume?
- Does OpenClaw use semantic retrieval, embeddings, graph traversal, or chunk-level source references?
- Does OpenClaw have operational audit logs for actions, not just answer context?
- Does OpenClaw have a clearer separation between draft artifacts, tasks, and knowledge records?

Likely best first merge target:

Add a minimal "Operational Follow-Ups" substrate to Vantage rather than trying to import a whole scheduler at once. A thin first slice could introduce:

- a `followups/` markdown store or equivalent record type,
- fields like `id`, `title`, `status`, `created_at`, `due_at`, `source_turn_id`, `source_record_id`, `summary`, `next_action`,
- meta action support for creating a follow-up from natural language,
- retrieval that pulls due/relevant follow-ups into Inspect,
- a small Inspect panel for open/completed/overdue follow-ups,
- tests proving ordinary timestamps still behave as metadata while follow-ups behave as commitments.

That would fit Vantage's existing architecture: local-first markdown, inspectable state, bounded retrieval, meta/executor writes, and product-facing audit receipts.

## Questions For The Next Alignment Pass

- Should Vantage become proactive, or only remember commitments for the next user-initiated turn?
- Should temporal commitments live as a new store, as artifacts, or as a memory subtype?
- Should due follow-ups appear in Chat, Inspect, Library, or all three?
- Should reminders ever fire outside an active browser session?
- Should Scenario Lab outputs be promotable from experiments before session deletion?
- Should the hidden Library dock become a first-class navigation surface before importing more saved-object types?
- Should OpenClaw features be ported as direct code, conceptual patterns, or new Vantage-native services?
