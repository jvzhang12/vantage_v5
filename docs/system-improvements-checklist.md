# System Improvements Checklist

## Purpose

This is the lightweight implementation backlog for improving Vantage as a whole.

Use this as the parent checklist while brainstorming. Detailed plans can branch into separate notes when an item becomes concrete enough to implement.

## Core Product

- [ ] Keep normal chat fast, natural, and low-friction.
- [ ] Make the difference between Chat, Whiteboard, Vantage, and Library obvious.
- [ ] Clarify lifecycle language for transient drafts, saved whiteboards, promoted artifacts, memories, and concepts.
- [ ] Evaluate attention-inspired concept terminology: `concept key` for routing identity and `concept value` for stored content.
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
- [ ] Decide whether `concept card` should become `concept key` in user-facing docs and UI while preserving internal compatibility.
- [ ] Avoid noisy automatic durable writes.
- [x] Add answer-basis payload and badge language for intuitive, memory-backed, protocol-guided, whiteboard-grounded, and mixed-context turns.
- [x] Keep protocol guidance separate from factual grounding in answer-basis payloads and UI.
- [ ] Keep grounding disclosures clear when an answer uses no recalled context.

## Library And Durable Stores

- [ ] Keep concepts, memories, artifacts, and reference notes visibly separate.
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
- [ ] Keep `learned` documented as the API field while allowing `Saved for Later` as UI copy.

## Open Backlog Items

- [ ] Decide whether whiteboard auto-save should produce artifact snapshots, recoverable drafts, or both in every case.
- [ ] Decide how visible draft history should be in the UI.
- [ ] Decide whether retained transient drafts should participate in Recall.
- [ ] Decide whether concept records should be explained as query/key/value objects, and where that language should appear.
- [ ] Decide how aggressively Vantage should invite the Whiteboard for work products.
- [x] Decide the current label set for answer-basis badges.
- [ ] Revisit the answer-basis label set after more product use.
- [ ] Define backend semantics before adding direct saved-item actions such as mark wrong, forget, or make temporary.
- [ ] Decide whether conversation resume should use Memory Trace reconstruction or a first-class thread snapshot.
- [ ] Decide which internal details belong in Vantage versus developer/debug surfaces.
