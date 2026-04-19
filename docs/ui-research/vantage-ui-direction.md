# Vantage UI Direction

This document turns the research and audit into a practical UI direction for Vantage.

It is deliberately close to the current repository.

It does not assume a full redesign or a new architecture.

## North Star

Vantage should feel like:

- a calm chat app by default
- a focused drafting tool when the whiteboard is open
- a guided inspection tool when the user opens `Vantage`

It should not feel like:

- an operator console
- a dashboard of simultaneous internal concepts
- a product that teaches its ontology before it helps

## Core Interaction Model

### Chat

Chat is the default.

It should answer:

`What did the assistant say, and do I need to act on anything right now?`

Chat should show:

- transcript
- composer
- compact evidence chips
- a single whiteboard invitation or draft-ready cue when relevant

Chat should not show:

- full reasoning trace
- candidate context
- large working-memory tables
- multiple simultaneous decision panels

### Whiteboard

Whiteboard is the active work surface.

It should answer:

`Where is the thing we are making together?`

When whiteboard is open:

- it should own the screen
- chat should become secondary
- drafting decisions should appear here, not duplicated elsewhere

### Vantage

`Vantage` is guided inspection.

It should answer:

- `What influenced this response?`
- `What was actually in scope?`
- `What changed because of this turn?`
- `What else exists in the library?`

It should not be the place where the user performs routine drafting.

## Proposed Vantage Structure

This section is future-facing.

It describes a recommended simplification target for the current `Vantage` surface.

It does not describe the exact shipped answer-dock structure today, which still centers the turn review around the current `Working Memory` framing with separate `Reasoning Path`, `Recall`, `Memory Trace`, and `Learned` sections.

### 1. This Turn

This should become the primary inspection frame.

Default contents:

- short answer summary
- compact grounding summary
- `Learned`
- one button or disclosure to open `Reasoning Path`

Expanded contents:

- `Working Memory`
- `Recall`
- `Memory Trace`
- `Reasoning Path`

But those should read as a hierarchy, not as unrelated sibling panels.

### 2. Scenario Lab

Only prominent when the current or recent turn used it.

It should stay visually distinct from normal turn inspection.

### 3. Library

This remains the home for:

- inspect
- search
- pin
- open in whiteboard
- related items

It should not compete with `This Turn` for first attention.

## Recommended Presentation Rules

### Outcome First

Every inspection view should start with:

- what the answer relied on
- what changed

Only then should it expose:

- what was considered
- what was excluded
- what was merely available

### One Parent Explanation

`Working Memory`, `Recall`, and `Memory Trace` should not feel like three unrelated cards.

Preferred hierarchy:

1. `This Turn`
2. `Working Memory`
3. inside that, `Recall` and `Memory Trace contribution`

### One Active Decision Zone

If the whiteboard is closed, the decision lives in chat.

If the whiteboard is open, the decision lives in whiteboard.

Do not show the same drafting decision across multiple surfaces simultaneously.

### One Verb Per Action

Prefer verbs that explain the actual effect:

- `Inspect`
- `Open in whiteboard`
- `Pin`
- `Find related`

Avoid ambiguous `Open` when multiple meanings are possible.

## Visual Direction

The visual problem is not only information architecture.

It is also density.

Vantage should move toward:

- fewer simultaneous bordered cards
- more whitespace between conceptual levels
- quieter metadata styling
- one strong heading per frame
- small chips for compact truth, not full subpanels for every noun

Recommended visual hierarchy:

- large title for the current surface
- one medium-weight summary card
- secondary disclosures beneath it
- low-contrast metadata until expanded

## Near-Term Recommendations

### Phase 1: Reduce Redundancy

- Introduce a single `This Turn` overview in `Vantage`.
- Collapse `Reasoning Path` by default.
- Keep `Candidate context` behind explicit expansion.
- Move turn-control affordances behind a small disclosure.

### Phase 2: Clarify Whiteboard Ownership

- Ensure whiteboard decisions appear in only one place at a time.
- Tighten whiteboard lifecycle language around transient draft, saved whiteboard, and promoted artifact.

### Phase 3: Calm The Metadata Layer

- Reduce simultaneous chips and micro-labels.
- Use fewer top-level badges in chat.
- Reserve dense labels for expanded `Vantage` inspection.

### Phase 4: Make Vantage Feel Premium

- Give `This Turn`, `Scenario Lab`, and `Library` visually distinct but quieter section treatments.
- Let `Scenario Lab` feel like a specialized reasoning mode rather than just another answer card.
- Keep `Library` powerful, but visually subordinate until the user chooses it.

## Translation Into Repo Terms

- `Chat` remains the main shell.
- `Whiteboard` remains the live shared draft.
- `Working Memory` remains the bounded in-scope generation context.
- `Recall` remains the vetted retrieved subset.
- `Memory Trace` remains recent searchable history.
- `Reasoning Path` remains the staged explanation, but secondary to a turn summary.
- `Library` remains the durable inspection/search surface.

The improvement target is not a new ontology.

The improvement target is a clearer and calmer expression of the ontology Vantage already has.
