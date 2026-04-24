# Vantage Evolution Implementation Plan

## Purpose

This document turns the current product vision for Vantage into an implementation plan that stays faithful to the repository as it exists today.

It is not a greenfield redesign.

It assumes the current repo already has the right major primitives:

- chat-first shell
- on-demand whiteboard
- Vantage as guided inspection
- bounded mixed retrieval
- Memory Trace
- Scenario Lab as a distinct routed mode

The core job now is to make these primitives feel coherent, trustworthy, and refined without drifting into brittle deterministic logic or an operator-console UI.

## Source Of Truth

This plan is grounded in:

- [AGENTS.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/AGENTS.md)
- [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
- [docs/codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md)
- [docs/working-memory-and-trace-model.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/working-memory-and-trace-model.md)
- [docs/reasoning-path.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/reasoning-path.md)
- [docs/implementation-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/implementation-roadmap.md)
- [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md)
- [docs/ui-research/vantage-ui-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)

For execution, every implementation or review wave should also read the mirrored summaries for the exact files in scope before editing or assessing code.

## Planning Read

The repository is already close to the intended product shape.

What remains is mostly:

- contract stabilization
- payload clarification
- retrieval and Memory Trace tuning
- UI composition and refinement
- documentation freshness

The main gaps are not missing systems.

The main gaps are:

- ambiguity around Working Memory versus Recall versus response-mode grounding
- compatibility alias drift across payloads
- brittleness concentrated in the client state/render layer
- Vantage feeling denser and more operator-like than intended
- whiteboard, chat, and Vantage still feeling too assembled rather than composed

## Critic Adjustments

This plan has already been reviewed by separate critic agents.

The plan below incorporates those corrections:

- do not invent a new `working_memory_state` DTO unless the current payload family proves insufficient
- use the existing `response_mode`, `turn_interpretation`, `workspace.context_scope`, and recall payloads as the main scope truth
- move frontstage calming work earlier so operator-console density is reduced sooner
- explicitly include `scenario_lab.py` and experiment-scoped storage where trace and learned semantics are touched
- treat alias cleanup as a later cleanup pass, not as a major early architectural wave
- require documentation sync inside each implementation wave, not as delayed follow-through

## Guardrails

- Keep the product chat-first.
- Keep Whiteboard separate from Library and from Vantage.
- Keep Working Memory, Recall, Memory Trace, Whiteboard, Learned, and Library semantically distinct.
- Use LLM reasoning for semantic interpretation, continuity, and routing.
- Use deterministic code for validation, boundedness, persistence, and UI state safety.
- Do not silently broaden context.
- Do not silently autosave whiteboard intent as durable learning.
- Do not backdoor heavier graph or retrieval architecture before the current bounded loop is clearly insufficient.

## Implementation Sequence

### Gate 1: Freeze The State And Payload Contract

Goal:

- stabilize the current whiteboard and surface contract before further product polish

What must become boring and predictable:

- surface transitions
- pending whiteboard carry
- `workspace_scope`
- `workspace.context_scope`
- selected-record continuity
- hidden-whiteboard out-of-scope behavior

Primary files:

- `src/vantage_v5/webapp/chat_request.mjs`
- `src/vantage_v5/webapp/surface_state.mjs`
- `src/vantage_v5/webapp/workspace_state.mjs`
- `src/vantage_v5/webapp/whiteboard_decisions.mjs`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/navigator.py`

Required checks:

- `tests/webapp_state_model.test.mjs`
- `tests/webapp_whiteboard_decisions.test.mjs`
- `tests/product_identity.test.mjs`
- `tests/test_server.py`

Definition of done:

- explicit whiteboard follow-up turns behave predictably
- refresh does not unexpectedly drop active draft continuity
- the active surface always matches the state model
- Vantage does not accidentally change whiteboard scope

### Gate 2: Post-Reliability Frontstage Calming

Goal:

- reduce the current operator-console feel once the core whiteboard and surface contract is stable

This gate exists because:

- the current product bar is calm chat and guided inspection
- payload truth alone will not make the product feel composed
- but reliability and state safety still gate UI composition work in the current repo

Primary work:

- keep chat compact and transcript-first
- ensure only one whiteboard cue is visible at a time
- reduce Vantage first-glance density
- start moving Vantage toward a `This Turn` first hierarchy
- codify the visual-density bar explicitly:
  - fewer simultaneous bordered cards
  - quieter metadata
  - one strong heading per frame
  - small chips instead of full subpanels where possible

Primary files:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/turn_payloads.mjs`

Definition of done:

- chat remains calm by default
- whiteboard decision ownership is singular and legible
- Vantage does not present three equally loud regions by default
- visual density is measurably reduced, not just rearranged

Required checks:

- `tests/product_identity.test.mjs`
- `tests/webapp_state_model.test.mjs`
- `tests/webapp_whiteboard_decisions.test.mjs`
- `tests/test_server.py`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Later Cleanup: Reduce Payload Drift One Alias Family At A Time

Goal:

- reduce compatibility ambiguity without breaking current consumers

Recommended order:

1. `record_id` vs `concept_id`
2. `workspace_update.status` vs `workspace_update.type`
3. `learned` vs `created_record`
4. `working_memory` alias cleanup last

Why this gate exists:

- alias drift is one of the easiest ways for frontend truth, backend truth, and documentation to diverge again
- but the repo already has most compatibility bridges in place, so this is cleanup rather than a new architectural prerequisite

Primary files:

- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/app.js`

Definition of done:

- each alias family has one canonical field and one compatibility story
- tests prove canonical behavior while keeping compatibility intact
- docs explicitly describe the transitional semantics

Required checks:

- `tests/test_server.py`
- `tests/product_identity.test.mjs`
- `tests/webapp_state_model.test.mjs`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 1: Stabilize Turn-Scope Contracts

Goal:

- stop conflating Recall with full Working Memory

Recommended contract:

- `recall`: vetted retrieved subset only
- `working_memory`: temporary compatibility alias for the narrower recall-shaped list
- full turn scope truth should continue to come from the existing payload family:
  - `response_mode`
  - `turn_interpretation`
  - `workspace.context_scope`
  - explicit selected-record continuity fields

Recommended implementation direction:

- improve frontend scope assembly around the existing contracts first
- only introduce a new canonical scope DTO if the existing payload family proves unable to express the needed truth without duplication

Primary files:

- `src/vantage_v5/server.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/navigator.py`
- `src/vantage_v5/services/response_mode.py`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/app.js`

Definition of done:

- frontend assembles scope truth from one explicit normalization path
- `response_mode` remains compact, not overloaded as the only scope authority
- Working Memory can be explained truthfully without inference from visible card lists

Required checks:

- `tests/test_server.py`
- `tests/product_identity.test.mjs`
- `tests/webapp_state_model.test.mjs`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 2: Harden Memory Trace As Structured Recent History

Goal:

- make `memory_trace/` trustworthy and inspectable without replaying transcripts or turning it into a graph

Recommended direction:

- keep Markdown trace records
- prefer extending existing structured trace/frontmatter signals over inventing a second trace subsystem
- keep Memory Trace as one bounded retrieval bucket inside the shared loop

Important scope:

- normal chat
- experiment-scoped traces
- Scenario Lab traces

Primary files:

- `src/vantage_v5/storage/memory_trace.py`
- `src/vantage_v5/storage/markdown_store.py`
- `src/vantage_v5/storage/experiments.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/services/search.py`
- `src/vantage_v5/server.py`

Definition of done:

- retrieval can rank trace records with metadata rather than body text alone
- UI can explain Memory Trace contribution truthfully
- Memory Trace stays separate from Library semantics
- experiment isolation and Scenario Lab trace behavior remain intact

Current repo status:

- landed as a focused pass: trace records now carry richer structured metadata, trace-aware search uses bounded recency and same-whiteboard continuity bonuses, turn payloads expose normalized Memory Trace metadata, and the required search/server/repo-hygiene checks pass

Required checks:

- `tests/test_search.py`
- `tests/test_server.py`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 3: Make Recall Continuity-Aware Without Hard Anchoring

Goal:

- tighten and tune the already-landed continuity behavior without redesigning it

Rules to stabilize:

- selected record stays in scope only when explicitly preserved
- if preserved, it consumes a bounded slot instead of becoming an unbounded side channel
- whiteboard, recent chat, and pending whiteboard remain separate from Recall
- memory-trace candidates remain their own retrieval source

Primary files:

- `src/vantage_v5/services/vetting.py`
- `src/vantage_v5/services/search.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/navigator.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/server.py`

Definition of done:

- continuity stays semantic, not hardcoded
- preserved context is visible and bounded
- hidden whiteboard does not silently ground ordinary chat

Required checks:

- `tests/test_search.py`
- `tests/test_server.py`
- `tests/product_identity.test.mjs`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 4: Make Learned Outcome-Truthful

Goal:

- distinguish durable learning from whiteboard lifecycle snapshots and promotions

Recommended direction:

- keep `learned[]` canonical
- prefer deriving UI truth from existing primitives where possible:
  - `MetaDecision.action`
  - executed action type
  - artifact snapshot signals
  - whiteboard lifecycle helpers
- add new cross-layer DTO fields only if the current primitives cannot express the required distinction cleanly

Primary files:

- `src/vantage_v5/services/meta.py`
- `src/vantage_v5/services/executor.py`
- `src/vantage_v5/services/chat.py`
- `src/vantage_v5/services/scenario_lab.py`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/app.js`

Definition of done:

- the UI can distinguish “learned concept” from “saved snapshot”
- auto artifact snapshots no longer masquerade as semantic learning

Required checks:

- `tests/test_server.py`
- `tests/product_identity.test.mjs`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 5: UI Composition Pass

Goal:

- make the product difference obvious without making chat heavy

Chat direction:

- keep compact evidence truthful
- keep only one visible whiteboard cue at a time
- avoid trace-rail or candidate-context spill into chat

Whiteboard direction:

- stronger drafting ownership when open
- quieter but clearer lifecycle cues
- no duplication of decisions across chat, whiteboard, and Vantage
- on smaller laptop widths, whiteboard must still remain visually primary

Recommended direction:

- add a stronger `This Turn` hierarchy
- collapse `Reasoning Path` by default
- subordinate Recall and Memory Trace under a parent explanation
- keep Candidate Context behind explicit expansion
- keep Scenario Lab distinct and conditional
- explicitly recompose the shell so `This Turn` is the default first-attention region
- prevent Library and Scenario Lab from competing with `This Turn` simultaneously when they are not in active use

Primary files:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/turn_payloads.mjs`
- `src/vantage_v5/webapp/whiteboard_decisions.mjs`
- `src/vantage_v5/webapp/workspace_state.mjs`

Definition of done:

- chat remains calm
- whiteboard feels like the main drafting environment when open
- lifecycle words match backend outcomes exactly
- users can answer “what shaped this response?” quickly
- Vantage starts with outcome and scope, not machinery
- Scenario Lab feels distinct without dominating ordinary turns
- the Vantage shell no longer reads as a three-dock dashboard by default
- the visual-density bar is enforced:
  - fewer simultaneous bordered cards
  - quieter metadata
  - one strong heading per frame
  - fewer competing chips and notices

Required checks:

- `tests/product_identity.test.mjs`
- `tests/webapp_state_model.test.mjs`
- `tests/webapp_whiteboard_decisions.test.mjs`
- `tests/test_server.py`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

### Phase 6: Library And Scenario Lab Polish

Goal:

- preserve both as powerful secondary surfaces without letting them crowd the main answer path

Primary files:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/services/scenario_lab.py` if durable revisit or reopen semantics change

Definition of done:

- Library remains powerful but visually secondary
- Scenario Lab reads as a first-class reasoning mode, not the default interaction model

Required checks:

- `tests/product_identity.test.mjs`
- `tests/test_server.py`
- `tests/test_repo_hygiene.py`
- `python scripts/check_repo_hygiene.py`

## Testing Expectations

At minimum, these suites should stay green as the plan advances:

- `tests/webapp_state_model.test.mjs`
- `tests/webapp_whiteboard_decisions.test.mjs`
- `tests/product_identity.test.mjs`
- `tests/test_server.py`
- `tests/test_search.py`
- `python scripts/check_repo_hygiene.py`

Manual checks should remain part of the contract for UI waves:

- hidden whiteboard does not ground ordinary chat
- open-whiteboard follow-ups continue the current draft naturally
- dirty draft survives refresh
- Vantage opened from whiteboard returns correctly
- Scenario Lab remains visible when relevant but quiet otherwise
- smaller laptop widths still keep the right surface visually primary

## Documentation Expectations

For every implementation wave that changes behavior or semantics, update:

- `README.md`
- `docs/working-memory-and-trace-model.md`
- `docs/reasoning-path.md`
- `docs/implementation-roadmap.md` when a roadmap section is effectively landed or superseded
- mirrored summaries under `docs/codebase/python/...`
- mirrored summaries under `docs/codebase/webapp/...`

Repo hygiene alone is not enough.

The docs must stay semantically fresh enough that future subagents can reason from them instead of from stale assumptions.

Documentation sync belongs inside the implementation wave itself, not in a delayed follow-up pass.

## Subagent Use Guidance

Use subagents for:

- isolated backend slices with exact file lists
- search ranking
- vetting continuity
- Scenario Lab durability slices
- review passes

Do not use subagents for:

- simultaneous edits across `app.js`, `server.py`, and shared DTO normalization
- alias-removal waves that touch both ends of the wire
- broad UI/state choreography in one pass
- integration-spine edits that all converge in `tests/test_server.py`
- deferring required docs sync until after the behavioral wave is already merged

Rule of thumb:

One orchestrator should own any wave that crosses client state, payload normalization, and server contract truth at once.

## Main Risks To Guard Against

- `working_memory` meaning different things in different layers
- frontend deriving scope truth from visible list length instead of backend payload truth
- hidden whiteboard grounding ordinary chat
- selected records bypassing vetting and becoming an unbounded context lane
- Memory Trace overpowering retrieval because of raw body text
- auto-saved artifact snapshots being presented as semantic learning
- experiment-scoped records leaking into durable retrieval or labels
- Vantage becoming denser as new panels are added instead of calmer as hierarchy improves
- documentation freshness falling behind the actual repo state
