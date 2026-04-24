# Vantage Refinement Pass 01

This pass is about making Vantage feel composed, elegant, and product-grade without changing its core semantics.

It is not a redesign of the architecture.

It is a visual-system and shell-refinement pass.

## Goal

Move Vantage away from the feeling of:

- a capable internal prototype
- a layout assembled from many truthful cards
- a UI where metadata competes with the work

Toward the feeling of:

- an authored product
- a calm default chat surface
- a premium drafting surface when the whiteboard is active
- a guided inspection surface when the user opens `Vantage`

## Design Principles

### One dominant surface at a time

- `Chat` is the main surface by default.
- `Whiteboard` becomes the main surface when drafting is active.
- `Vantage` becomes the main inspection surface when explicitly opened.

No secondary panel should visually compete with the active surface.

### Typography before containers

The interface should rely more on:

- spacing
- type scale
- tone
- alignment
- restrained dividers

and less on:

- stacked bordered boxes
- repeated subpanel framing
- heavy visual separators

### Metadata should feel supporting, not primary

Labels such as:

- `Recall`
- `Learned`
- `Best Guess`
- whiteboard lifecycle
- route or grounding summaries

should read as compact signals first.

Deep explanation still exists, but it should live behind inspection or disclosure.

### Whiteboard should feel editorial

The whiteboard is where the shared work lives.

It should feel closer to:

- a document
- a page
- a canvas for authored text

than to:

- another utility panel
- a textarea in a tool dashboard

### Vantage should feel guided, not mechanical

The first impression of `Vantage` should answer:

- what shaped this response
- what changed
- what else exists in the library

It should not lead with retrieval machinery or expose too many equally weighted blocks at once.

## Visual System Intent

### Tone

- warm, quiet, paper-forward
- refined and editorial rather than glossy
- serious enough for thought work, but not austere

### Color

- keep the warm paper background
- narrow the accent system
- reduce competing highlight hues
- use stronger contrast only for meaningful action and selection

### Type

- serif-led titles and document surfaces
- restrained sans-serif for controls, labels, metadata, and chips
- tighter heading hierarchy
- quieter metadata sizing

### Surfaces

- fewer visible layers at once
- gentler borders
- more solid surfaces, less translucent noise
- one strong visual treatment per surface instead of many similar card treatments

### Motion

- subtle hover and focus motion
- no decorative movement
- transitions should reinforce which surface is primary

## Scope For Pass 01

### In

- shell spacing and hierarchy
- chat header and transcript refinement
- message card refinement
- button hierarchy cleanup
- whiteboard surface refinement
- Vantage dock refinement
- lower-contrast metadata treatment

### Out

- major semantic restructuring
- changing retrieval or response logic
- renaming product concepts
- rebuilding the Vantage information architecture

Those belong to later passes.

## Concrete Implementation Targets

### Chat

- reduce perceived chrome in the header
- make the transcript feel lighter and more readable
- soften message card treatment so the answer content carries more weight than the container
- keep evidence visible, but visually secondary

### Whiteboard

- make the whiteboard header feel like a drafting workspace rather than a control bar
- make the editor feel like a premium page
- center the document with stronger page margins and calmer framing
- keep lifecycle copy visible but quiet

### Vantage

- reduce the “many sibling cards” feeling
- make dock summaries cleaner and more deliberate
- keep inspection dense enough to be useful, but calmer in default presentation

## Acceptance Criteria

This pass succeeds if:

- the product no longer feels like a prototype made of many bordered cards
- the whiteboard feels like the most premium surface in the product
- chat feels calmer and easier to read
- `Vantage` feels intentional rather than dashboard-like
- the visual system reads as consistent across all three surfaces

## Follow-On Passes

After this pass, the next likely refinements are:

1. simplify `Vantage` around a stronger `This Turn` hierarchy
2. reduce metadata density further in chat and inspection
3. give `Scenario Lab` a more distinct premium identity
4. tighten responsive behavior for smaller laptop widths
