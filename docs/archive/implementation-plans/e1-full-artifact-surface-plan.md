# E1 Full Artifact Surface Plan

## Purpose

This document turns `E1. Full Artifact Surface` from the roadmap into a concrete, repository-true implementation plan.

It is intentionally narrower than a full new product surface.

The current repo already has:

- a `Whiteboard` as the live collaborative drafting surface
- durable `Artifacts` stored in Markdown
- library inspection and reopen flows inside `Vantage`
- automatic whiteboard iteration snapshots
- explicit whiteboard promotion into artifacts

So E1 should expand and clarify those existing seams rather than introduce a fourth major surface.

## Current Truth

The current codebase already implies an artifact product model:

- `Whiteboard` is the editable live draft.
- `Artifacts` are durable work products in the `Library`.
- opening an artifact into the whiteboard is already a handoff path, not a new storage type.
- saving the whiteboard already creates a durable artifact snapshot on every `/api/workspace` save.
- promotion already marks a stronger lifecycle transition than ordinary save.
- Scenario Lab already treats the comparison as a durable revisit hub while keeping branches as reopenable whiteboard workspaces.

Key current seams:

- [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py)
- [src/vantage_v5/services/executor.py](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/executor.py)
- [src/vantage_v5/storage/artifacts.py](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/storage/artifacts.py)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [docs/glossary.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)
- [docs/implementation-roadmap.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/implementation-roadmap.md)

## Product Goal

Make durable artifacts feel like first-class work products without displacing the whiteboard as the only live drafting surface.

The user should be able to understand:

- what the current whiteboard draft is
- what durable artifact was last saved from it
- how to inspect that durable artifact
- how to reopen that artifact into the whiteboard when they want to keep working
- how a promoted artifact differs from an ordinary saved whiteboard snapshot

## Non-Goals

E1 should not:

- add a new top-level artifact editing surface
- make artifacts another always-open panel beside chat, whiteboard, and `Vantage`
- blur `Artifacts` with `Memory Trace`
- introduce full revision lineage or branching history as a first-class model
- require richer structured storage than the current Markdown-first artifact records can reliably support

Those belong to deferred `E2` or later architecture work.

## Canonical E1 Rules

These rules should guide implementation:

1. `Whiteboard` remains the only live editable drafting surface.
2. `Artifact` remains a durable saved work product in the `Library`.
3. Artifact interaction is inspect-first and reopen-into-whiteboard second.
4. E1 should deepen the existing `Vantage` + `Library` artifact path rather than add a separate artifact route.
5. Whiteboard iteration snapshots and promoted artifacts should feel related, but not identical.
6. Scenario Lab’s “durable revisit hub” framing is the best current model for ordinary artifact review copy.

## Proposed User Experience

### 1. Whiteboard Save Becomes Legible

When the whiteboard is saved, the user should see more than “saved whiteboard.”

The product should surface:

- that a durable artifact snapshot was created
- the identity of the latest saved artifact
- a direct `Inspect artifact` action
- a direct `Reopen saved version` or equivalent reopen action only when it adds value

This uses data the server already returns through `artifact_snapshot`.

### 2. Artifact Review Becomes Richer Inside Vantage

Artifacts should get a clearer review presentation inside the existing library inspector.

That should answer:

- what kind of artifact this is
- whether it came from the whiteboard
- whether it is the latest durable save from the current draft
- whether it is a promoted artifact or an iteration snapshot
- what the main reopen action is

This is an inspector enhancement, not a new surface.

### 3. Reopen Semantics Become More Explicit

Artifact reopen behavior should read as:

- inspect the durable version in `Vantage`
- reopen that durable version into the whiteboard when the user wants to continue editing

The product should not imply that inspecting an artifact automatically pins it into future working memory or turns it into the live draft.

### 4. Promotion Reads As Stronger Than Snapshot

The current repo already distinguishes:

- ordinary whiteboard iteration snapshots
- promoted artifacts

E1 should make that distinction clearer in copy and inspector cues, while still letting both live inside the `Artifacts` bucket.

## Implementation Slices

### E1-A. Latest Durable Artifact Visibility

Goal:

- expose the latest artifact created from whiteboard saves as a first-class cue in the current whiteboard flow

Primary effect:

- whiteboard save stops feeling like a silent durability side effect

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/styles.css`
- optionally `src/vantage_v5/webapp/product_identity.mjs` if lifecycle copy is centralized there

Tests to add or update:

- `tests/webapp_state_model.test.mjs` if a small helper is extracted
- small render-focused webapp test if artifact-snapshot presentation logic is split out

Documentation to update:

- `docs/codebase/webapp/src/vantage_v5/webapp/app.js.md`
- `docs/codebase/webapp/src/vantage_v5/webapp/index.html.md`
- `docs/codebase/webapp/src/vantage_v5/webapp/styles.css.md`

Acceptance:

- after saving the whiteboard, the user can immediately tell that a durable artifact exists
- the user has a direct inspect path without hunting through the library

### E1-B. Artifact Inspector Enrichment

Goal:

- make the existing artifact inspector feel intentional and artifact-specific

Primary effect:

- `Artifacts` stop reading like generic saved-note cards

Likely additions:

- artifact-origin cues such as “saved from whiteboard” or “promoted from whiteboard”
- stronger lifecycle labels
- reopen copy that matches current behavior
- optional use of existing metadata such as `comes_from`, `type`, and Scenario Lab metadata

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/server.py` only if more artifact metadata must be serialized for the client
- `src/vantage_v5/storage/artifacts.py` only if needed metadata is present in storage but not surfaced cleanly

Tests to add or update:

- `tests/test_server.py` if artifact payload serialization changes
- focused webapp render/state test if artifact inspector helpers are extracted

Documentation to update:

- `docs/codebase/python/src/vantage_v5/server.py.md`
- `docs/codebase/python/src/vantage_v5/storage/artifacts.py.md`
- `docs/codebase/webapp/src/vantage_v5/webapp/app.js.md`

Acceptance:

- artifact review answers “what is this durable thing?” without forcing the user to infer from raw markdown alone
- ordinary artifacts and Scenario Lab comparison hubs feel like siblings, not unrelated UI species

### E1-C. Reopen And Continuation Cue Pass

Goal:

- make artifact reopen behavior feel boring and explicit

Primary effect:

- users understand that artifacts are durable saved versions and the whiteboard is where continued editing happens

Scope:

- tighten labels like `Open`, `Reopen in whiteboard`, `Inspect artifact`
- align ordinary artifact reopen language with Scenario Lab’s comparison-hub language
- ensure the client does not imply inspection equals continuity

Files to touch:

- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`
- `src/vantage_v5/webapp/index.html`
- `README.md` if repo-level product language changes

Tests to add or update:

- `tests/product_identity.test.mjs`
- any focused webapp label/helper tests

Documentation to update:

- `docs/glossary.md` if terminology gets sharper
- `docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md`
- `docs/codebase/webapp/src/vantage_v5/webapp/app.js.md`

Acceptance:

- the product clearly distinguishes inspect vs reopen vs continue editing
- artifact reopen behavior matches what the backend already does

## Recommended Delivery Order

Deliver E1 in this order:

1. `E1-A. Latest Durable Artifact Visibility`
2. `E1-B. Artifact Inspector Enrichment`
3. `E1-C. Reopen And Continuation Cue Pass`

This order matters because:

- `E1-A` uses an existing backend return path and gives immediate user value
- `E1-B` can then deepen the existing review path without inventing a new one
- `E1-C` should come after the new inspect/reopen affordances are visible enough to refine

## What To Reuse

E1 should explicitly reuse these existing patterns:

- whiteboard lifecycle labels from `deriveWhiteboardLifecycle()`
- library inspection as the main durable-object review path
- Scenario Lab’s durable comparison-hub framing
- `artifact_snapshot` returned from `/api/workspace`
- existing artifact reopen flow through `open_saved_item_into_workspace()`

## What To Avoid

Do not do these as part of E1:

- a dedicated top-level artifact page
- inline artifact editing outside the whiteboard
- automatic artifact continuity into working memory just because it was inspected
- revision history UI beyond the current snapshot/promote distinction
- new storage requirements that assume full lineage metadata on every artifact

## Open Questions To Resolve Before Implementation

These should be answered at kickoff, not improvised mid-wave:

1. Should the latest durable artifact cue live only inside the whiteboard surface, or also in chat-level notices?
2. Should a promoted artifact replace the “latest durable artifact” cue, or should snapshots and promoted artifacts remain separately labeled?
3. What is the minimal metadata the client needs to distinguish “ordinary whiteboard snapshot,” “promoted artifact,” and “Scenario Lab comparison hub” without forcing a storage migration?
4. Should ordinary artifacts ever get a stronger subtype label in the UI, or is lifecycle copy enough for now?

## Recommended Definition Of Done

E1 is done when:

- the user can save a whiteboard and immediately see that a durable artifact now exists
- artifacts feel intentionally inspectable in `Vantage`
- reopening an artifact into the whiteboard feels explicit and unsurprising
- the whiteboard remains the only live editing surface
- no new top-level surface or hidden continuity model is introduced

## Handoff Note

If implementation starts, preserve this scope boundary:

`E1 is about making the current artifact path visible and product-legible. It is not revision lineage, not artifact-native editing, and not a new surface model.`
