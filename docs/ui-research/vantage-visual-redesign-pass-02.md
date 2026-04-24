# Vantage Visual Redesign Pass 02

This pass is not another subtle refinement.

It is a stronger visual redesign pass intended to make Vantage feel:

- visually intuitive
- clearly differentiated by surface
- calm but intentional
- ready to ship

It still does not change the underlying architecture.

It changes how the architecture is expressed.

## Why Pass 01 Was Not Enough

Pass 01 improved:

- hierarchy
- shell clarity
- metadata density
- whiteboard focus behavior
- Scenario Lab ordering

But it was deliberately conservative.

That means it mostly improved correctness and composure without creating enough first-impression change.

The result is a UI that is better organized but can still feel:

- too similar to the earlier prototype
- too card-driven
- too cautious in visual voice
- too dependent on internal structure improvements that the user may not notice at a glance

Pass 02 should solve that gap directly.

## Current Status

Pass 02 is now fully implemented in the current frontend:

- 02A rebuilt the chat visual voice
- 02B turned the whiteboard into a more editorial drafting surface
- 02C reframed `Vantage` as a guided narrative
- 02D gave Scenario Lab a flagship comparison presentation
- 02E tightened the shared visual system so the product feels like one authored whole

The remaining work after Pass 02 should focus on semantics, interaction trust, and product affordances rather than on another broad styling rewrite.

## New Goal

When a user opens Vantage, the product should immediately feel like:

- a real conversation product in chat
- a real authored drafting surface in whiteboard
- a real guided-inspection product in `Vantage`
- a real reasoning mode in Scenario Lab

The user should not need to notice the ontology first to feel the product quality.

## Core Design Shift

Pass 01 mostly asked:

`How do we make the current structure calmer?`

Pass 02 asks:

`How should each surface feel, visually and emotionally, when it is the primary surface?`

This is a different question.

It means:

- stronger surface contrast
- more opinionated typography
- fewer mid-emphasis elements
- more dramatic reduction of generic panel language
- more visible primary/secondary/tertiary distinction

## Target Surface Feel

### Chat

Chat should feel:

- fluid
- typographic
- conversational
- lightly framed

The user should feel that the answer is the product.

Not:

- the shell
- the panel
- the evidence rail
- the controls

Desired visual signals:

- larger and more comfortable answer text
- less visible outer framing around the transcript
- more air between turns
- softer or less “utility-card” message treatment
- metadata that feels supportive, not co-equal

### Whiteboard

Whiteboard should feel:

- authored
- editorial
- document-like
- intentionally premium

The user should feel that this is the shared work surface.

Desired visual signals:

- clear page-like center of gravity
- stronger document margins
- richer title treatment
- calmer surrounding controls
- stronger contrast between the draft itself and supporting UI

### Vantage

`Vantage` should feel:

- guided
- sequential
- inspectable
- explanatory instead of dashboard-like

The user should feel that they are opening a layered explanation.

Desired visual signals:

- one clear narrative spine for `This Turn`
- lower visual weight on secondary regions
- fewer visible “parallel cards”
- a stronger sense of progressive disclosure
- less apparent retrieval machinery on first open

### Scenario Lab

Scenario Lab should feel:

- distinct
- premium
- strategic
- comparison-first

It should be a signature capability, not just another answer format.

Desired visual signals:

- question and recommendation clearly centered
- comparison hub clearly presented as the durable anchor
- branch cards easier to scan
- branch reopen/inspect actions easier to understand
- support rationale clearly secondary

## What Must Be Visibly Different

This pass should create visible change in the following places:

### 1. Typography

- stronger heading scale
- more editorial use of serif titles
- better transcript reading scale
- quieter metadata text
- clearer difference between answer copy, UI chrome, and diagnostic detail

### 2. Containers

- fewer generic rounded boxes
- less repeated “card around every noun”
- more use of spacing and tone instead of borders
- more deliberate primary surface framing

### 3. Surface Contrast

Chat, Whiteboard, and `Vantage` should no longer feel like slight variations of the same layout.

They should feel materially different:

- `Chat`: conversational
- `Whiteboard`: authored
- `Vantage`: reflective

### 4. Visual Hierarchy

The UI should make harder choices about what is primary:

- answer first
- draft first
- explanation first

Not:

- everything somewhat important at once

### 5. Product Identity

Scenario Lab and guided inspection should feel like distinct product capabilities, not implementation details dressed up with labels.

### 6. Shared System Coherence

After the surface-specific passes land, the whole product should still feel visibly related:

- one restrained spacing rhythm
- fewer medium-emphasis borders and tinted cards
- calmer, more intentional secondary controls
- stronger consistency in primary / secondary / tertiary emphasis
- a quieter overall product frame

## Anti-Patterns To Avoid

Pass 02 should not:

- introduce a flashy visual style that fights the product’s seriousness
- turn `Vantage` into a console aesthetic
- make whiteboard feel like a Figma clone or a text editor clone
- hide truthful evidence entirely
- break the current semantic distinctions between `Working Memory`, `Recall`, `Memory Trace`, and Library
- overload the home chat surface with premium styling that hurts readability

The goal is:

- more authored
- not more ornamental

## Visual Redesign Priorities

### Priority 1: Chat Must Look More Intentional

If the default surface still feels similar, the whole product will still feel similar.

This is the most important visible gap.

### Priority 2: Whiteboard Must Look Like The Best Surface

Whiteboard should reward the user immediately for opening it.

### Priority 3: Vantage Must Look More Guided And Less Boxy

The information architecture is already improved.

The next need is a clearer visual storytelling layer.

### Priority 4: Scenario Lab Must Feel Like A Signature Mode

The current logic is strong enough.

The presentation needs to catch up.

## Acceptance Criteria

This pass is succeeding when:

- the user immediately notices that chat looks more refined
- whiteboard feels like a real drafting surface rather than an app panel
- `Vantage` feels like guided inspection rather than a collection of truthful boxes
- Scenario Lab feels like a product feature with its own gravity
- the product feels ship-ready even before the user understands its full ontology

## Relationship To Existing Docs

This pass extends:

- [vantage-ui-direction.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)
- [vantage-refinement-pass-01.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-refinement-pass-01.md)

Pass 01 remains valid.

But Pass 02 changes the bar:

- from `calmer and cleaner`
- to `visibly differentiated and ship-ready`
