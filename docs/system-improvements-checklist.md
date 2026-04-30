# System Improvements Checklist

## Purpose

This is the lightweight implementation backlog for improving Vantage as a whole.

Use this as the parent checklist while brainstorming. Detailed plans can branch into separate notes when an item becomes concrete enough to implement.

## Core Product

- [ ] Keep normal chat fast, natural, and low-friction.
- [ ] Make the difference between Chat, Whiteboard, Vantage, and Library obvious.
- [ ] Clarify lifecycle language for transient drafts, saved whiteboards, promoted artifacts, memories, and concepts.
- [x] Evaluate attention-inspired concept terminology: accept `concept key/value` only as an advanced design metaphor.
- [ ] Keep user-facing language consistent with the current product vocabulary.

## Navigator And Control Panel

- [ ] Treat Navigator as the main semantic interpreter for turn intent.
- [ ] Move scattered intent heuristics behind Navigator control-panel actions over time.
- [ ] Expand Navigator eval cases for common product flows.
- [ ] Make Navigator decisions inspectable without making the UI feel technical.
- [ ] Keep deterministic code focused on validation, persistence, and safety.

## Whiteboard

- [ ] Make whiteboard opening, drafting, editing, and returning feel predictable.
- [ ] Preserve active drafts across refreshes, navigation, and app restarts.
- [ ] Keep draft application non-destructive when another draft is already active.
- [ ] Add recoverable draft retention with warnings before cleanup.
- [ ] See [whiteboard-draft-retention-todo.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/whiteboard-draft-retention-todo.md).

## Memory And Retrieval

- [ ] Keep Working Memory bounded and truthful.
- [ ] Improve Recall quality across Memory Trace, concepts, memories, artifacts, and reference notes.
- [ ] Clarify when information becomes a concept versus a memory versus an artifact.
- [x] Decide that `Concept Card` remains canonical terminology; document key/value only as an advanced metaphor while preserving `card`, `body`, and `links` / `links_to`.
- [ ] Avoid noisy automatic durable writes.
  - [x] Add a narrow guard for obvious test/probe/freshness-marker prompts so they do not become durable concepts.
  - [x] Implement backend saved-item correction semantics for `mark_incorrect` and `forget` as hide/suppress actions.
  - [x] Add Saved for Later `Hide as incorrect` and `Don't use again` controls backed by the correction route.
  - [ ] Add saved-item freshness/confidence labels only after the correction UI flow and semantics are product-tested.
- [x] Add answer-basis payload and badge language for intuitive, memory-backed, protocol-guided, whiteboard-grounded, and mixed-context turns.
- [x] Keep protocol guidance separate from factual grounding in answer-basis payloads and UI.
- [x] Add a Context Budget receipt in Inspect for included / excluded turn context.
- [x] Keep grounding disclosures clear when an answer uses no recalled context.

## Library And Durable Stores

- [x] Keep concepts, memories, artifacts, and reference notes visibly separate.
- [ ] Make saved-item reopen flows reliable and non-destructive.
- [ ] Improve artifact lifecycle metadata and presentation.
- [ ] Keep protocols as guidance objects rather than drafts or evidence.
- [ ] Decide how much of the Library should be visible in the simplified Vantage surface.

## Scenario Lab

- [ ] Keep Scenario Lab separate from ordinary chat and whiteboard drafting.
- [ ] Improve follow-up behavior on existing scenario comparisons.
- [ ] Make branch workspaces and comparison artifacts easier to inspect and reopen.
- [ ] Strengthen Scenario Lab protocol guidance and eval coverage.

## Frontend Experience

- [ ] Continue consolidating surface state across Chat, Whiteboard, and Vantage.
- [ ] Reduce surprising layout changes.
- [ ] Keep compact evidence visible in chat without turning chat into an inspection panel.
- [x] Add intuitive answer-basis badges that distinguish model-only intuition from memory-backed, protocol-guided, whiteboard-grounded, and mixed-context answers.
- [x] Add the first read-only `Saved for Later` review slice over the canonical `learned` payload.
- [ ] Improve lifecycle cues for drafts, saved items, and learned items beyond the first review slice.
- [ ] Keep Vantage useful as an inspection surface without overwhelming the main workflow.

## Persistence And Multi-User

- [ ] Keep local-first storage simple and inspectable.
- [ ] Preserve user-profile isolation in multi-user mode.
- [ ] Make logout/login continuity robust so users can resume recent conversation and active whiteboard work.
- [ ] Make experiment-mode writes clearly session-local, including `Learned` / `Saved for Later` review items that represent saved outcomes from the turn even when their scope is temporary.
- [ ] Improve backup, cleanup, and retention behavior for runtime state.
- [ ] Keep deployment defaults private and conservative.

## Testing And Evaluation

- [ ] Add small product-behavior evals before changing routing behavior.
- [ ] Keep focused tests near the module boundaries they protect.
- [ ] Use Navigator evals for semantic routing drift.
- [ ] Use frontend state tests for whiteboard and surface transitions.
- [ ] Keep repo hygiene checks passing as files and mirrored docs evolve.

## Documentation

- [ ] Keep README aligned with actual repo behavior.
- [ ] Keep architecture docs current when module responsibilities change.
- [ ] Keep implementation plans separate from canonical product semantics.
- [ ] Link detailed child plans from this checklist as they emerge.
- [ ] Keep `learned` documented as the API field while allowing `Saved for Later` as UI copy for turn-created/saved items, not verification, freshness, or confidence.

## Open Backlog Items

- [ ] Decide whether whiteboard auto-save should produce artifact snapshots, recoverable drafts, or both in every case.
- [ ] Decide how visible draft history should be in the UI.
- [ ] Decide whether retained transient drafts should participate in Recall.
- [x] Decide that query/key/value language belongs only in advanced design explanation, not ordinary UI, API, or schema vocabulary.
- [ ] Decide how aggressively Vantage should invite the Whiteboard for work products.
- [x] Decide the current label set for answer-basis badges.
- [ ] Revisit the answer-basis label set after more product use.
- [x] Implement backend semantics for saved-item `mark_incorrect` and `forget` as hide/suppress corrections.
- [x] Expose supported Saved for Later correction actions in the UI as hide/suppress controls, not hard delete.
- [ ] Keep `make_temporary`, direct saved-item edit, hard delete, freshness, and confidence actions out of the correction route until separately specified.
- [ ] Decide whether conversation resume should use Memory Trace reconstruction or a first-class thread snapshot.
- [ ] Decide which internal details belong in Vantage versus developer/debug surfaces.
