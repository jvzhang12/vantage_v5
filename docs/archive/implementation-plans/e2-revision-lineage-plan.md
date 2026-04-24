# E2 Revision Lineage Plan

## Purpose

This document turns `E2. Revision Lineage As First-Class Product Behavior` from the roadmap into a concrete, repository-true implementation plan.

It is intentionally narrower than a full revision-control system.

The current repo already has lineage primitives:

- Markdown-backed records with `links_to` and `comes_from`
- record revision support in `markdown_store.create_revision()`
- concept-specific revision support through `ConceptStore.create_revision()`
- executor support for `create_revision`
- artifact provenance through `comes_from`
- lineage-aware retrieval signals
- basic lineage visibility in the UI through badges and metadata

So E2 should clarify and productize those existing seams rather than introduce a second persistence model or a Git-like history surface.

## Current Truth

The current codebase already implies a lightweight lineage model:

- `create_revision()` exists in the shared Markdown store and writes a new file with a `--vN` suffix.
- revisions inherit `type` and default card semantics from the base record.
- revisions currently encode ancestry through `comes_from`, with the base record id placed first.
- `ConceptStore` exposes revision creation directly.
- `GraphActionExecutor` can execute `create_revision`, but the meta layer does not expose revision as a normal write action today.
- artifacts already use `comes_from` for whiteboard provenance and Scenario Lab comparison ancestry.
- search already scores against lineage fields, so ancestry can affect retrieval.
- the UI can already display `comes_from`, `links_to`, and a human label for `create_revision`, but there is no first-class revision inspector flow.

That means the repo already has lineage data, but not yet a stable product contract for what lineage means.

## Product Goal

Make revision lineage inspectable and trustworthy without:

- turning the whiteboard into version control
- widening Working Memory by default
- blurring concepts, memories, and artifacts into one generic saved-item model
- making reopen semantics imply continuity when the user only inspected something

The user should eventually be able to understand:

- whether a durable item is a new record or a revision
- what record it came from
- whether a relationship is semantic (`links_to`) or ancestral (`comes_from`)
- whether they are inspecting a durable revision or reopening it into the whiteboard to keep working

## Non-Goals

E2 should not:

- add a graph-history console or DAG browser
- auto-create revisions for every save or every edit
- turn artifacts, concepts, and memories into one generic versioned type
- replace the existing Markdown-first stores with a new revision database
- treat search ranking as the authoritative lineage model
- pin revision ancestry into Working Memory unless the user intentionally brings it into scope

Those belong to later architecture work, if at all.

## Canonical E2 Rules

These rules should guide implementation:

1. `Revision` means an explicit derivative of a durable saved record, not merely a similar or related item.
2. `links_to` remains a semantic-neighborhood relation, not a lineage relation.
3. `comes_from` remains the current canonical provenance field unless and until a narrower lineage field is deliberately introduced.
4. `Inspect` and `Reopen in whiteboard` remain different actions.
5. Whiteboard saves continue to create artifact snapshots, not implicit revisions.
6. Artifact provenance and concept revision should be surfaced clearly, but they should not be collapsed into one generic user-facing noun.
7. Revision lineage should stay inspect-first before it becomes a routine visible write action.
8. The first visible E2 slice should be read-only inspection and payload truth, not a new default write button.
9. The first revision-capable slice should treat concept revision as a single-base relation, not a general multi-parent lineage system.

## Existing Architectural Constraints

### 1. Lineage Is Currently Generic Provenance

The same `comes_from` field currently carries:

- whiteboard-to-artifact provenance
- Scenario Lab comparison ancestry
- revision ancestry for Markdown record revisions

That is acceptable today, but E2 should not overclaim that every `comes_from` relation is a formal revision chain.

### 2. Meta Does Not Yet Offer Revision As A Normal Write

`MetaService` currently exposes:

- `no_op`
- `create_concept`
- `create_memory`
- `promote_workspace_to_artifact`

So the product does not currently promise automatic or routine revision creation. E2 should respect that and avoid making revision feel more implemented than it is.

### 3. Search Already Uses Lineage Signals

Retrieval already scores `comes_from` and `links_to`.

That means E2 must avoid overweighting lineage in a way that makes parents or older revisions appear more relevant than the current durable record.

### 4. Reopen Semantics Are Still Too Generic

`open_saved_item_into_workspace()` currently reopens any saved record into the whiteboard, but the executor action naming still reflects older concept-oriented assumptions.

E2 should tighten the meaning of inspect vs reopen before it adds more lineage affordances.

## Proposed User Experience

### 1. Lineage Reads As Guided Inspection First

Inside `Vantage` and the library inspector, the user should be able to see:

- `Derived from <record>`
- `Revision of <record>` when that relationship is explicit enough to claim
- the difference between semantic links and ancestry

This should feel like guided inspection, not a raw metadata dump.

### 2. Revision Remains A Deliberate Durable Action

The first E2 slice should not add a generic always-on `Revise` button in chat.

Instead, it should:

- make lineage visible and trustworthy
- normalize the record payload shape
- clarify which records are reopenable into the whiteboard
- preserve the current “create first, revise later when explicit” product posture

### 3. Artifact Provenance Becomes More Legible

Artifacts should more clearly answer:

- was this saved from the whiteboard?
- was this promoted?
- is this an iteration snapshot?
- what whiteboard or parent item did it come from?

That is provenance-first, not necessarily revision-first.

## Implementation Slices

### E2-A. Canonical Lineage Payload And Inspector Contract

Goal:

- make lineage and provenance payloads explicit and inspectable without changing write behavior yet

Primary effect:

- the UI can distinguish semantic links, provenance, and explicit revision ancestry truthfully

Files likely to touch:

- `src/vantage_v5/server.py`
- `src/vantage_v5/services/executor.py`
- `src/vantage_v5/storage/markdown_store.py`
- `src/vantage_v5/storage/artifacts.py`
- `src/vantage_v5/webapp/app.js`

Likely contract work:

- normalize record lineage payloads for concepts and artifacts
- expose explicit inspector-friendly labels such as `derived_from`, `revision_parent`, or equivalent computed payload fields if needed
- preserve `comes_from` as the storage truth unless a narrow compatibility-safe alias is helpful
- tighten selected-record and reopen semantics so inspection does not imply continuity

Acceptance:

- the UI can tell the user what a saved item came from without implying more than the backend knows
- inspect, reopen, and provenance cues stop feeling interchangeable

### E2-B. Concept Revision As A Deliberate First-Class Action

Goal:

- make concept revision a visible but constrained durable action

Primary effect:

- the product can represent “this should become a new version of an existing concept” without overwriting the old concept

Files likely to touch:

- `src/vantage_v5/services/meta.py`
- `src/vantage_v5/services/executor.py`
- `src/vantage_v5/storage/concepts.py`
- `src/vantage_v5/storage/markdown_store.py`
- `src/vantage_v5/webapp/app.js`

Guardrails:

- keep concept revision separate from artifact promotion
- require an explicit target/base concept
- treat the first concept-revision slice as single-base, even if `comes_from` remains a broader provenance list underneath
- do not make revision the fallback for ordinary concept creation
- keep duplicate suppression and neighborhood linking behavior intact

Acceptance:

- a deliberate revision action can create a new concept revision with inspectable ancestry
- nearby concepts still use `links_to` rather than fake revision ancestry

### E2-C. Artifact Provenance And Revision Cues

Goal:

- make artifact ancestry legible without pretending artifacts have the same lifecycle as concepts

Primary effect:

- saved outputs feel like durable work products with clear provenance instead of generic notes

Files likely to touch:

- `src/vantage_v5/storage/artifacts.py`
- `src/vantage_v5/server.py`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/product_identity.mjs`

Scope:

- improve inspector language for saved whiteboard iterations vs promoted artifacts
- surface when an artifact came from a whiteboard or comparison branch set
- keep reopen behavior explicit and boring

Acceptance:

- artifact ancestry is understandable without introducing artifact-as-version-control semantics

Implementation status:

- landed: executor and Scenario Lab now stamp explicit artifact lifecycle metadata, server/chat serializers expose it, and the UI renders whiteboard snapshots, promoted artifacts, and comparison hubs with explicit lifecycle wording instead of generic derived-item language

## Recommended Sequence

Land the slices in this order:

1. `E2-A` payload and inspector truth pass
2. `E2-B` constrained concept revision action
3. `E2-C` artifact provenance and lifecycle cue pass

Why this order:

- payload truth and inspect semantics should stabilize before adding a more visible revision action
- concept revision already has the cleanest backend footing
- artifact ancestry is important, but it should build on clarified terminology rather than lead it

## Risks To Avoid

The first implementation pass should avoid:

- overloading `comes_from` in the UI as if it always means revision-parent
- surfacing lineage in a way that quietly widens Working Memory
- making search/ranking appear to define ancestry truth
- introducing a revision button before the inspect/reopen distinction is stable
- implying branch/merge/version-control capabilities the repo does not implement

## Documentation And Test Expectations

If E2 moves from plan to implementation, update:

- `README.md` if user-facing revision language changes
- `docs/semantic-rules.md` if lineage semantics become a new rule
- codebase docs for touched storage, executor, server, and webapp files

Tests should cover:

- canonical lineage payload serialization
- concept revision execution with explicit parent/base record
- inspect vs reopen behavior for lineage-rich records
- artifact provenance rendering
- regression coverage so lineage does not silently broaden Working Memory disclosures

## Definition Of Done

E2 is done when:

- revision lineage is visible and truthful
- provenance and semantic links are distinguishable
- inspect and reopen actions are explicit
- concept revision can be deliberate without becoming the default for all durable writes
- artifacts feel lineage-aware without turning the product into a history console
