# Vantage V5 Current-Repo Implementation Plan

## Purpose

This document turns the current Vantage V5 roadmap into a concrete implementation plan that stays faithful to the repository as it exists today.

It is intentionally grounded in:

- the current repo behavior in `README.md`
- the current implementation-vs-canon note in `docs/implementation-vs-canon.md`
- the current codebase maps under `docs/codebase/`

This is not permission to backdoor older, heavier architecture into the repo.

The goal is to improve the existing product shape:

- chat-first interaction
- on-demand whiteboard drafting
- guided inspection through `Vantage`
- bounded retrieval across concepts, memories, artifacts, and reference notes
- Scenario Lab as a separate navigator-routed reasoning mode

For execution details, use [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) as the handoff contract for implementation and review subagents.

## Source Of Truth Order

When using this plan, follow this source-of-truth order:

1. `README.md` for current product and runtime truth
2. `docs/glossary.md` for canonical product semantics
3. `docs/semantic-rules.md` for implementation-facing behavioral boundaries
4. `docs/implementation-vs-canon.md` for current-repo vs future-state clarification
5. `docs/codebase/README.md` and the mirrored file summaries
6. older canonical product and architecture docs only when they do not conflict with current repo truth

When this roadmap is being executed by subagents, the orchestration protocol is the companion document that defines how to split, scope, and review the work.

If this plan appears to conflict with current code or current repo docs, current repo truth wins.

## Current-State Assumptions

This plan assumes the following foundations already exist in the repo and should be hardened rather than re-invented:

- the client already has three major surfaces: `chat`, `whiteboard`, and `Vantage`
- the client already has a surface enum and snapshot-based continuity helpers
- normal chat already uses `response_mode`, `workspace_update`, and `turn_interpretation`
- whiteboard offers and whiteboard drafts are already conservative and pending by default
- the server already uses `workspace_scope` to decide when whiteboard content is in scope
- Scenario Lab is already navigator-routed and separate from the normal `/api/chat -> search -> vet -> reply -> meta -> executor` loop
- retrieval is already mixed and bounded, but still mainly lexical-plus-vetting rather than semantic-first

Because of that, the first implementation waves are mostly stabilization and hardening work, not greenfield feature work.

## Current Memory Trace Note

The first `Memory Trace` migration slice is now active in the repo:

- `src/vantage_v5/storage/memory_trace.py` is the markdown-backed recent-history store
- normal chat writes both JSON debug traces and markdown memory-trace records
- retrieval can include recent `memory_trace` candidates in Recall
- the Library surface remains concept / memory / artifact oriented rather than absorbing Memory Trace

## Product Promise

The working product promise for these implementation waves is:

`Vantage helps you think with inspectable working memory, durable notes, and shared drafting without making normal chat feel heavy.`

## Guardrails

- Keep the product chat-first.
- Keep the whiteboard as the drafting surface, not as a permanent operator console.
- Keep `Working Memory`, `Learned`, `Whiteboard`, and `Library` visibly separate.
- Use LLM reasoning for semantic interpretation and continuity judgments.
- Use deterministic code for validation, persistence, conservative routing boundaries, and UI state safety.
- Do not silently save pending drafts or whiteboard offers.
- Do not rename internal `workspace_*` API or storage fields during the early UX hardening waves.
- Do not introduce warm-cache, graph-heavy, or embedding-heavy architecture until the current bounded retrieval loop is clearly insufficient.

## Track A: Reliability And State Safety

This is the gating track. It should land before more UI polish.

### A1. Complete Surface-State Consolidation

Goal:

- finish the shift from ad hoc client flags to one authoritative surface model
- make chat, whiteboard, and Vantage transitions derive from the same rules

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/surface_state.mjs`

Tests to update:

- `tests/webapp_state_model.test.mjs`

Key coverage:

- chat -> whiteboard
- whiteboard -> Vantage -> whiteboard
- snapshot restore after refresh

Major risk:

- `app.js` still performs some direct surface assignment; changing that can easily break whiteboard return behavior or snapshot restoration

Definition of done:

- surface transitions are predictable
- the active layout always matches the current surface
- returning from Vantage preserves the expected draft context

### A2. Tighten Whiteboard Continuity In Local State

Goal:

- make the active draft survive passive refresh, draft application, destructive opens, and ordinary follow-up edits
- preserve the current non-destructive fork-vs-replace behavior for pending drafts

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/workspace_state.mjs`
- `src/vantage_v5/webapp/whiteboard_decisions.mjs`

Tests to update:

- `tests/webapp_state_model.test.mjs`
- `tests/webapp_whiteboard_decisions.test.mjs`

Key coverage:

- dirty draft preservation
- replace vs append vs keep-current
- local unsaved draft continuity when a new draft arrives

Major risk:

- simplifying the local draft flow can accidentally reintroduce destructive overwrite behavior

Definition of done:

- active drafts stop unexpectedly disappearing
- accepting or applying a draft does not erase unrelated unsaved work
- the client continues to prefer non-destructive draft handling

### A3. Align Client Carry Rules With Server Whiteboard Interpretation

Goal:

- make accepted offers, explicit “open whiteboard” requests, and edit-follow-up turns behave as one coherent continuation flow
- make `workspace_scope` the real source of truth end to end

Files to touch:

- `src/vantage_v5/webapp/chat_request.mjs`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/navigator.py`

Tests to update:

- `tests/webapp_state_model.test.mjs`
- `tests/test_server.py`

Key coverage:

- `shouldCarryPendingWorkspaceUpdate()`
- `buildWorkspaceContextPayload()`
- whiteboard accept flow
- visible whiteboard edit follow-up
- hidden whiteboard out-of-scope behavior
- `requested` vs `visible` vs `pinned`

Major risk:

- client-side carry heuristics and server-side interpretation can drift apart and cause “why did it offer again?” regressions

Definition of done:

- explicit whiteboard requests do not re-trigger unnecessary confirmation
- follow-up drafting turns update the current draft when appropriate
- hidden whiteboards do not silently ground ordinary chat

### Reliability Gate

Do not move to Track B until the following are true:

- whiteboard drafts survive refresh and ordinary navigation
- surface transitions are stable
- explicit whiteboard follow-up turns behave predictably
- focused state tests cover the main drafting and navigation paths

## Track B: Product Legibility

This track should make the product difference obvious without opening Vantage every turn.

### B1. Vocabulary And Lifecycle Cue Pass

Goal:

- finish the user-facing terminology cleanup
- keep internal `workspace_*` mechanics intact while making user-visible language consistent

Files to touch:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/services/executor.py`
- `README.md`

Tests to update:

- `tests/product_identity.test.mjs`
- `tests/test_server.py` where promotion/open flows surface lifecycle cues

User-facing language to stabilize:

- `Whiteboard`
- `Working Memory`
- `Learned`
- `Library`
- `Transient draft`
- `Saved whiteboard`
- `Promoted artifact`

Major risk:

- visible copy cleanup must not be coupled to an early API/storage rename

Definition of done:

- a new user can distinguish whiteboard, Working Memory, and Library from the UI alone
- lifecycle cues match actual backend outcomes

### B2. Strengthen Compact Evidence In Chat

Goal:

- make transcript-level evidence tell the truth about what supported the answer
- keep evidence driven by backend payload truth, not client guesswork

Files to touch:

- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/services/chat.py`

Tests to update:

- `tests/product_identity.test.mjs`
- `tests/test_server.py`

Key coverage:

- working-memory grounded
- whiteboard-only grounded
- recent-chat-only grounded
- pending-whiteboard carry-over
- mixed-context
- true best-guess
- learned durable write

Major risk:

- if the frontend infers more than the backend reports, the product will overclaim grounding quality

Definition of done:

- chat surfaces whether the answer used recalled items, the whiteboard, recent chat, learned something durable, or is a best guess

### B3. Refocus Vantage As Guided Inspection

Goal:

- keep the existing Vantage surface, but make the first screen answer three questions immediately:
  - what influenced this response?
  - what did the system learn?
  - what else relevant exists?

Files to touch:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- `src/vantage_v5/webapp/app.js`

Tests to update:

- add focused helper tests only if small UI logic is extracted
- otherwise rely on state/evidence tests plus manual verification

Major risk:

- `index.html` structure and `app.js` element ids are tightly coupled; broad markup edits can destabilize the UI

Definition of done:

- Vantage feels like guided inspection, not a raw operator console
- the first screen is understandable at a glance

## Track C: Retrieval And Context Usefulness

This track improves usefulness inside the current architecture instead of replacing it.

### C1. Retrieval Ranking And Candidate Shaping

Goal:

- improve first-pass recall inside the current lexical-plus-vetting model
- score phrase matches and metadata signals more intelligently
- prevent one source bucket from dominating weak result sets

Files to touch:

- `src/vantage_v5/services/search.py`
- `src/vantage_v5/storage/markdown_store.py`
- `src/vantage_v5/storage/vault.py`

Tests to update:

- `tests/test_search.py`

Key coverage:

- artifact vs memory tie cases
- path-driven or lineage-like matches
- mixed-source ranking cases
- use of `card`, `links_to`, and source-weighting signals

Major risk:

- overfitting ranking to fixtures while relying on vetting to hide regressions

Definition of done:

- relevant user facts, artifacts, and concepts surface more reliably before vetting
- retrieval remains mixed and bounded

### C2. Continuity-Aware Vetting And Context Assembly

Goal:

- preserve the right continuity anchor when the user is clearly continuing an active draft, pinned context, or a Scenario Lab comparison artifact
- keep LLM vetting as the semantic selector rather than replacing it with rigid deterministic anchoring

Files to touch:

- `src/vantage_v5/services/vetting.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`

Tests to update:

- `tests/test_server.py`

Key coverage:

- follow-ups after artifact promotion
- selected-record continuation
- scenario comparison revisits with stable comparison-artifact branch metadata
- continuity anchor preserved without crowding out the rest of the 5-item working set

Major risk:

- too much deterministic anchoring will make retrieval feel brittle and over-constrained

Definition of done:

- continuity follow-ups keep the right anchor more often
- working memory remains bounded and mixed

### C3. Whiteboard In-Scope Contract And DTO Cleanup

Goal:

- harden the `workspace_scope` contract
- migrate toward one canonical request/response shape only after the frontend is fully on the current fields
- execute this wave under [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) so implementation and review stay tightly scoped

Files to touch:

- `src/vantage_v5/webapp/chat_request.mjs`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/services/executor.py`
- `README.md`

Tests to update:

- `tests/test_server.py`

Key coverage:

- canonical `pinned_context_id`, with `selected_record_id` retained only as a compatibility alias at the public/client seam
- canonical `learned`, with `created_record` treated as the compatibility alias
- canonical `record_id`
- canonical `workspace_update.status`
- truthful `response_mode`
- whiteboard out-of-scope turns

Major risk:

- removing aliases too early will break the UI

Definition of done:

- the frontend no longer depends on redundant payload aliases
- whiteboard scope behavior is visible and truthful in the returned payloads

### C4. Memory Trace Store And Recall Wiring

Goal:

- harden and extend the markdown-backed `Memory Trace` slice that now sits alongside the existing JSON debug traces under `traces/`
- tune recent trace items as a distinct continuity source
- keep letting retrieval feed those recent items into Recall without turning the UI into a raw trace viewer

Files to touch:

- `src/vantage_v5/storage/memory_trace.py`
- `src/vantage_v5/services/search.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/server.py`
- `src/vantage_v5/storage/experiments.py`
- `docs/codebase/python/README.md`
- `docs/codebase/python/src/vantage_v5/storage/memory_trace.py.md`
- `docs/codebase/python/src/vantage_v5/services/chat.py.md`
- `docs/codebase/python/src/vantage_v5/server.py.md`
- `docs/reasoning-path.md`

Tests to update:

- `tests/test_search.py`
- `tests/test_server.py`

Current status:

- `memory_trace/` is live for normal chat and Scenario Lab turns
- retrieval can already surface `memory_trace` candidates
- recent trace ranking now has structured metadata signals in frontmatter, so trace scope and grounding can outrank body-only matches
- Memory Trace frontmatter now also carries turn mode, recalled ids/sources, learned ids/sources, history count, and preserved-context ids, and those fields are exposed back through turn payloads for inspection
- recent trace ranking now also applies bounded continuity bonuses for same-whiteboard recency and preserved-context matches without turning traces into a hard side channel

Key coverage:

- recent trace records persist independently of JSON debug traces
- retrieval can surface recent trace items as a distinct candidate source
- recent trace metadata can influence ranking separately from transcript body text
- current-turn payloads can expose Memory Trace metadata truthfully without turning the UI into a raw trace browser
- Recall can include trace-backed items when they are relevant
- UI disclosures still distinguish Recall from other grounded context

Major risk:

- if Memory Trace is exposed too loudly, it will blur the line between bounded recall and the raw turn history

Definition of done:

- the repo has a clear markdown-backed recent-history layer alongside `traces/`
- retrieval can use that layer without collapsing it into the Library or the whiteboard
- grounding disclosures still read naturally as Recall vs other grounded context

Implementation status:

- landed: Memory Trace now stores richer structured frontmatter, retrieval uses bounded recency / whiteboard / preserved-context bonuses for trace candidates, and turn payloads expose normalized trace metadata for inspection

## Track D: Scenario Lab As A Durable Reasoning Product

This track should make Scenario Lab more reusable and revisit-friendly, not just prettier.

### D1. Durable Scenario Model Cleanup

Goal:

- make the comparison artifact the stable revisit hub
- standardize stable branch metadata and reopen behavior without changing the repo’s basic Markdown-first storage model

Files to touch:

- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/server.py`
- `src/vantage_v5/services/navigator.py`
- `src/vantage_v5/storage/workspaces.py`
- `src/vantage_v5/storage/artifacts.py`

Tests to update:

- `tests/test_server.py`

Key coverage:

- branch reopen
- detached namespace behavior
- comparison-artifact follow-up continuity
- stable scenario metadata on saved outputs

Major risk:

- the current branch model is still filename-first Markdown storage, so structured scenario metadata should stay modest and practical

Definition of done:

- users can reopen and continue Scenario Lab outputs without forcing a rerun
- comparison artifacts behave like durable reasoning products

### D2. Scenario Lab UI Productization

Goal:

- make Scenario Lab read as a distinct reasoning mode inside the current product
- surface the comparison question, recommendation, branch assumptions, risks, the saved comparison artifact’s branch roster, and stronger reopen/inspect actions
- use the saved comparison artifact as the durable comparison hub without requiring more backend orchestration

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- `src/vantage_v5/webapp/turn_payloads.mjs`

Tests to update:

- keep backend payload assertions in `tests/test_server.py`
- add focused webapp tests only if small helpers are extracted

Major risk:

- overdesigning Scenario Lab could make Vantage feel heavier instead of clearer

Definition of done:

- Scenario Lab feels like a first-class reasoning mode
- revisit and inspection actions are obvious
- the saved comparison hub is the clearest reopen/inspect path, while richer branch detail still lives alongside it

## Deferred Architecture Checkpoint

These are not normal implementation waves yet.

They should be revisited only after Tracks A through D feel trustworthy.

### E1. Full Artifact Surface

Questions to revisit later:

- when is a whiteboard draft too large or too durable for the whiteboard surface?
- do long-form plans, essays, or papers need a distinct artifact-oriented surface?

Concrete planning doc:

- `docs/archive/implementation-plans/e1-full-artifact-surface-plan.md`

Status:

- implemented as a focused pass without introducing a separate artifact surface

### E2. Revision Lineage As First-Class Product Behavior

Implementation plan:

- `docs/archive/implementation-plans/e2-revision-lineage-plan.md`

Questions to revisit later:

- should concept revision become a standard visible action?
- should artifact lineage become more explicit than today’s conservative creation-first behavior?

Files that would matter later:

- `src/vantage_v5/services/meta.py`
- `src/vantage_v5/services/executor.py`
- `src/vantage_v5/storage/markdown_store.py`
- `src/vantage_v5/storage/artifacts.py`
- `src/vantage_v5/storage/concepts.py`

Status:

- partially implemented:
  - E2-A lineage payload and inspector contract pass landed
  - E2-B constrained concept-revision action landed
  - E2-C artifact provenance cue pass landed: whiteboard snapshots, promoted artifacts, and Scenario Lab comparison hubs now carry explicit artifact lifecycle fields through write, serialization, and UI rendering

### E3. Heavier Retrieval Architecture

Explicitly defer for now:

- full embedding infrastructure
- warm-cache retrieval
- graph-heavy reranking
- whole-graph or concept-workspace loading

Status:

- deferred

## Recommended Implementation Sequence

### Wave 1: Reliability Gate

Land:

- A1. Complete Surface-State Consolidation
- A2. Tighten Whiteboard Continuity In Local State
- A3. Align Client Carry Rules With Server Whiteboard Interpretation

Why first:

- this is the highest-trust issue in the product right now
- if drafts feel unstable, later polish does not matter

### Wave 2: Product Legibility

Land:

- B1. Vocabulary And Lifecycle Cue Pass
- B2. Strengthen Compact Evidence In Chat
- B3. Refocus Vantage As Guided Inspection

Why second:

- once the state model is trustworthy, the product difference should become visible without opening internals every turn

### Wave 3: Retrieval And Scope Truth

Land:

- C1. Retrieval Ranking And Candidate Shaping
- C2. Continuity-Aware Vetting And Context Assembly
- C3. Whiteboard In-Scope Contract And DTO Cleanup
- C4. Memory Trace Store And Recall Wiring

Why third:

- this improves actual usefulness without changing the repo’s fundamental architecture
- this is where recent searchable history starts to become real

### Wave 4: Scenario Lab Productization

Land:

- D1. Durable Scenario Model Cleanup
- D2. Scenario Lab UI Productization

Why fourth:

- Scenario Lab should become more reusable after the core chat/whiteboard behavior is reliable

### Checkpoint: Deferred Architecture

Revisit only after the first four waves feel stable:

- E1. Full Artifact Surface
- E2. Revision Lineage
- E3. Heavier Retrieval Architecture

## What Not To Do Yet

- Do not rename `workspace_*` fields during early UX hardening.
- Do not introduce a new surface model or a frontend framework migration.
- Do not replace semantic routing with more brittle client-side keyword logic.
- Do not treat older canon as already-implemented architecture.
- Do not add a separate artifact UI surface before the current whiteboard and artifact flows are stable.
- Do not make broad automatic concept revision the default.

## Acceptance Checklist

This plan is succeeding when the following are true:

- chat still feels natural and light
- whiteboard drafts remain stable across refreshes and follow-up edits
- the user can tell what influenced the answer
- the user can tell what the system learned
- hidden whiteboards do not ground ordinary chat by accident
- the client and server agree on whiteboard continuation behavior
- retrieval feels more useful without losing boundedness
- recent searchable history is available through Memory Trace without collapsing it into the Library
- Scenario Lab feels revisit-friendly and distinct

## Documentation Rule For Every Wave

Every implementation wave should update, in the same change:

- touched source files
- touched tests
- mirrored summaries under `docs/codebase/python/...` or `docs/codebase/webapp/...`
- `README.md` when the repo-level product contract changes

This plan should evolve as the current repo closes or redefines the gap with future-state canon.
