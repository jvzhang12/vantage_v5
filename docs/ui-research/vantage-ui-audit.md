# Vantage UI Audit

This is a local audit of the current Vantage UI structure and terminology.

It is intentionally grounded in the repository's present architecture rather than an abstract redesign.

## What Is Already Strong

- The semantic model is better than the current presentation.
- The distinction between `Working Memory`, `Recall`, `Memory Trace`, `Whiteboard`, `Library`, and `Learned` is strong and worth preserving.
- The product is already moving toward the right surface split: `Chat`, `Whiteboard`, and `Vantage`.
- `Reasoning Path` is a good idea when it stays inspectable instead of ambient.

## Highest-Priority Pain Points

### 1. One Turn Is Explained In Too Many Parallel Blocks

The current answer-review area makes the user reconcile overlapping descriptions of the same turn across:

- `Working Memory`
- `Answer summary`
- `Recall`
- `Memory Trace`
- `Learned`
- `Reasoning Path`

The result is not lack of information.

The result is lack of hierarchy.

### 2. Reasoning Path Opens Too Deep Too Early

When the first prominent open state is `Candidate context`, the user meets retrieval machinery before they have a clear top-level answer to:

`What shaped this answer?`

That makes `Vantage` feel closer to a debugging console than a guided explanation.

### 3. Whiteboard Decisions Are Semantically Correct But Spatially Scattered

The same whiteboard event can appear across:

- chat invite UI
- whiteboard-side decision UI
- evidence chips
- notices
- `Vantage` disclosures

This makes the product feel uncertain about where drafting decisions belong.

### 4. The Library Teaches Too Much At Once

The distinction between:

- inspect
- open in whiteboard
- pin
- related items

is good, but it is taught through repeated explanatory copy rather than one obvious interaction model.

### 5. Metadata Density Is Too High

The user frequently sees too many of these at once:

- grounding badges
- recall counts
- source chips
- memory-trace labels
- decision-source labels
- continuity labels
- notices
- lifecycle badges

That hurts intuition even when each individual label is truthful.

## Strong Concepts With Weak Presentation

### Working Memory / Recall / Memory Trace

The concepts are strong.

The presentation problem is that they appear as sibling panels instead of one parent-child explanation.

### Open / Pinned / In Scope

The semantics are clear in the docs.

The presentation problem is too much instructional language and too little obvious affordance design.

### Whiteboard

The whiteboard is correctly treated as an on-demand drafting mode.

The presentation problem is that it often shows up first as a decision workflow instead of simply the place where the draft lives.

### Scenario Lab

Scenario Lab is correctly modeled as a separate routed mode.

The presentation problem is that it is explained in too many surfaces at once.

## Simplify, Merge, Defer, Hide, Rename

### Simplify

- Keep one primary turn frame inside `Vantage`: `This Turn`.
- Let that frame own the short answer to “what influenced this response?”

### Merge

- Merge default turn-review content into a single parent overview rather than several sibling cards.
- Keep the underlying data, but reduce simultaneous top-level sections.

### Defer

- Push `Candidate context` and full scope-table detail behind explicit expansion.
- Default `Reasoning Path` to an outcome-first or working-memory-first view.

### Hide

- Hide advanced turn controls like `remember`, `don't save`, and related-item actions behind a small disclosure.
- Keep them available, but not inside the main explanatory frame.

### Rename

- `Candidate context` → `Considered`
- `Open` → `Open in whiteboard`
- `Open related now` → `Find related in Library`
- `What did the system learn?` → `Learned` or `Saved from this turn`

## Suggested Information Architecture

### Chat

Default home.

Should contain:

- transcript
- composer
- compact evidence
- at most one active whiteboard invitation or draft-ready cue

### Whiteboard

Drafting mode.

Should contain:

- editor
- lifecycle
- save/promote controls
- the one active whiteboard decision area

### Vantage

Inspection mode.

Its first level should be:

- `This Turn`
- `Library`
- conditional `Scenario Lab`

### Library

Should remain inside `Vantage`, not as a top-level peer surface.

### Reasoning Path

Should remain inside `This Turn`, collapsed by default.

## Principles For Future UI Work

- One surface should answer one primary user question.
- Show outcome first, mechanism second, raw candidate detail last.
- Use one visible label per concept.
- Put decisions where the user can act on them, and only there.
- Keep inspection read-only by default.
- Require explicit pinning for carry-forward context.
- Preserve semantic distinctions without teaching all of them at once.
- Let chat advertise product differentiation with compact evidence, not control-panel density.
