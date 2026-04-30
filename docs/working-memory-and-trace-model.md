# Working Memory And Trace Model

## Purpose

This document defines the current product vocabulary for:

- the live collaborative drafting surface
- the automatically captured recent history
- the bounded context sent to the LLM for generation

It is the canonical semantic model for the current `vantage-v5` migration phase.

Use this document when updating:

- UI copy
- retrieval behavior
- turn payloads
- trace storage
- whiteboard behavior
- implementation planning

## Canonical Terms

### Whiteboard

`Whiteboard` is the live shared draft the user and the LLM are working on.

It is:

- a collaborative surface
- editable
- current
- user-visible
- not automatically identical to the durable library

The whiteboard may contribute to current-turn generation context when it is in scope, but it is not the same thing as Working Memory.

### Memory Trace

`Memory Trace` is the automatically captured recent history of the system.

Every user request should create memory trace, whether or not a whiteboard is active.

Memory Trace is:

- automatic
- recent-history oriented
- searchable
- recallable
- bounded by retrieval rather than dumped wholesale into generation

Memory Trace is not the same thing as the Library.
It is also not the same thing as the chat transcript.

It is the structured recent-history layer that Vantage can search when deciding what is relevant now.

In the current repo, Memory Trace is persisted as markdown-backed records in `memory_trace/`, separate from the JSON debug traces under `traces/`.

### Working Memory

`Working Memory` is everything that is materially in scope and sent to the LLM for generation of the current response.

Working Memory should include only the bounded subset actually used for the turn.

Typical contributors are:

- current user message
- bounded recent chat
- whiteboard content when in scope
- recalled memory-trace items
- recalled library items
- applied or recalled protocols when the current task needs reusable guidance
- selected or pinned context when intentionally preserved
- pending whiteboard context when intentionally carried into the turn

Working Memory must remain:

- bounded
- inspectable
- truthful

The current API exposes the narrower recall-shaped subset as top-level `recall`, while legacy `working_memory` remains a compatibility alias for that subset.

### Library

`Library` is the curated durable saved layer.

It includes:

- concepts
- memories
- artifacts
- reference notes

The Library is not the same thing as Memory Trace.

Saved-item corrections can hide or suppress Library records from recall without erasing the underlying history.

`mark_incorrect` and `forget` correction actions should remove the target item from Library listing, recall, and saved-item search through hidden/suppressed correction semantics. They should not become hard deletes, freshness labels, confidence labels, direct edits, or make-temporary actions.

### Recall

`Recall` should be treated primarily as a process or sub-step rather than the main top-level product noun.

The system recalls relevant items from:

- Memory Trace
- Library
- other explicitly preserved context sources
- applied protocols selected by the protocol interpreter or Navigator control panel

Those recalled items may then enter Working Memory.

Protocols are a special case: they are guidance for how to perform the task, not factual evidence. A protocol can be relevant even when it is not semantically close to the user's wording, because the Navigator may intentionally apply it before response generation.

Recalled items now carry lightweight taxonomy fields when available:

- `kind`: product object kind such as protocol, concept, memory trace, memory, artifact, or reference.
- `memory_role`: how the item functioned, such as instruction, durable knowledge, episodic trace, saved work, or reference.
- `recall_status`: whether the item was available, selected/recalled, learned, or logged.
- `source_tier`: whether it came from built-in guidance, experiment state, durable storage, recent trace, or reference material.

The Inspect UI uses these fields plus response-mode context sources to separate `Protocol`, `Used`, `Recent`, and `Draft` buckets without treating protocol guidance as factual evidence.

## Core Model

The current conceptual stack is:

- `Whiteboard` = the live draft
- `Memory Trace` = the recent searchable history
- `Working Memory` = the bounded model input for this turn
- `Library` = the curated durable saved layer

Compact rule:

`Whiteboard is the live draft. Memory Trace is the searchable history. Working Memory is what the model sees.`

## Key Distinctions

These distinctions should not drift.

### Whiteboard Is Not Working Memory

The whiteboard is a surface.

Working Memory is a turn-level generation payload.

The whiteboard may be part of Working Memory when it is in scope, but it is not equivalent to Working Memory.

### Memory Trace Is Not Library

Memory Trace is recent and automatically captured.

Library is curated and durable.

Something can be present in Memory Trace without being promoted into the Library.

### Memory Trace Is Not Raw Transcript Replay

Memory Trace should be structured and searchable.

It should capture recent continuity without requiring the system to replay entire conversations verbatim into the model.

### Working Memory Is Not Everything Recent

Everything recent should be traceable and recallable.

Only a bounded relevant subset should enter Working Memory.

This preserves boundedness and interpretability.

## Minimum Memory Trace Contract

Every turn should create a memory trace record.

At minimum, a trace record should be able to carry:

- turn id
- timestamp
- user message
- assistant message
- whiteboard id when applicable
- whiteboard snapshot or excerpt when applicable
- working-memory summary
- recalled items used for the turn
- learned or saved records created from the turn
- experiment or session scope when applicable

This does not mean all of that must always be shown to the user.

It means the system should preserve enough structured recent history to support recall and inspection later.

## Current Retrieval Model

The current retrieval pool is mixed and bounded.

The system searches:

1. recent Memory Trace records
2. concepts
3. saved notes, including memories and artifacts
4. reference notes from the vault

The system then vets that candidate pool and chooses what actually enters Working Memory.

Hidden or suppressed saved records should be filtered before they can enter Recall or Working Memory.

The whiteboard contributes to generation only when it is intentionally in scope; it is not currently a separate search bucket in the retrieval pipeline.

This preserves the product rule:

- everything recent is traceable
- everything recent is recallable
- not everything recent is automatically in Working Memory

## UI Implications

The product should use this language:

- `Whiteboard`
- `Memory Trace`
- `Working Memory`
- `Library`
- `Recall`

Recommended UI meanings:

- `Whiteboard`: the live collaborative draft
- `Memory Trace`: recent searchable history and continuity
- `Working Memory`: the full bounded in-scope generation context
- `Recall`: the narrower retrieved subset that fed the answer
- `Library`: durable saved knowledge and outputs

`Recall` can still appear in implementation or inspection details, but it should not be the main user-facing noun if `Working Memory` is the clearer top-level concept.

## Migration Guidance

### Workspace

`Workspace` should be treated as a deprecated implementation term.

Near-term rule:

- backend compatibility aliases such as `workspace_id` may remain temporarily
- user-facing copy should prefer `Whiteboard`
- new implementation and docs should prefer `whiteboard` over `workspace`

### Working Memory Payload Semantics

The product meaning should stay:

- full bounded generation context

The narrower retrieved subset remains exposed as `recall`, with `working_memory` retained as a compatibility alias until payload migration is complete.

## Recommended Next Steps

1. Keep the glossary aligned with this vocabulary.
2. Keep `memory_trace/` as the markdown-backed recent-history store.
3. Keep the retrieval pool mixed and bounded across traces, concepts, saved notes, and reference notes.
4. Keep whiteboard context intentional rather than passive.
5. Keep `Working Memory` as the top-level explanation of what the model saw for the turn.
6. Keep the Library separate from recent trace so the system does not collapse curated memory and automatic continuity into one bucket.
7. Keep protocols available as explicit task guidance for recurring work types and reasoning modes, while labeling them separately from factual sources.
8. Keep saved-item corrections as hide/suppress semantics for `mark_incorrect` and `forget`, with freshness/confidence and scope/edit mutations deferred.
