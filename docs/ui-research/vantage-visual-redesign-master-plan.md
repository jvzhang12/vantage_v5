# Vantage Visual Redesign Master Plan

This document turns the current UI research into an implementation-ready redesign plan for the existing Vantage architecture.

It sits one layer above the earlier direction notes and one layer below code changes.

Use it when the goal is to make Vantage feel:

- visually calmer
- more premium
- more intuitive by surface
- more ready to ship

without changing the underlying product ontology.

## What This Plan Is For

This plan is for:

- translating stylistic research into buildable frontend slices
- giving subagents concrete constraints for `Chat`, `Whiteboard`, `Vantage`, and later `Scenario Lab`
- keeping future visual passes aligned with current repository semantics

This plan is not for:

- redefining product nouns
- changing backend truth contracts
- inventing a new surface model
- using styling changes as a substitute for semantic clarity

## Source Docs

This plan consolidates:

1. [vantage-stylistic-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-stylistic-direction.md)
2. [stylistic-inspiration-elements.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/stylistic-inspiration-elements.md)
3. [vantage-visual-redesign-pass-02.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-pass-02.md)
4. [vantage-visual-redesign-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-checklist.md)
5. [external-feedback-follow-on-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-follow-on-roadmap.md)
6. [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)
7. [docs/semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md)

## Canonical Semantics To Preserve

These visual passes must preserve the current repo meanings of:

- `Working Memory`: the full in-scope context used for generation
- `Recall`: the retrieved subset inside that broader working context
- `Memory Trace`: the searchable recent-turn trace, distinct from both `Recall` and durable library material
- `Whiteboard`: the live shared draft between the user and the model
- `Learned`: what changed durably because of the turn, or what the current UI truthfully presents as learned under the existing product contract
- `Library`: durable stored material available for future retrieval or inspection
- `Scenario Lab`: a distinct reasoning mode for branch comparison
- `Pinned Context`: explicit carry-forward scope
- `open` or `inspect`: visible or selected, but not automatically in scope

Do not blur:

- `Working Memory` and `Recall`
- `Recall` and `Memory Trace`
- `Whiteboard` and `Vantage`
- `open` and `pinned`
- `inspect` and `edit`
- `Experiment Mode` and top-level interface surfaces

`Experiment Mode` remains a session boundary, not a peer product surface beside `Chat`, `Whiteboard`, or `Vantage`.

## Primary Implementation Levers

Every redesign pass should work these levers in this order:

1. layout density and surface hierarchy
2. metadata collapse and progressive disclosure
3. action visibility and grouping
4. typography hierarchy and spacing rhythm
5. color, iconography, and finishing detail

If a pass mainly changes colors, badges, or decorative styling without improving the first three items, it is probably not solving the real problem.

## Shared Design Rules

These rules apply across all visual passes.

### Surface Priority

At any moment, one surface should clearly lead:

- `Chat` leads by default
- `Whiteboard` leads during drafting
- `Vantage` leads only when the user explicitly chooses inspection

No view should feel like multiple equal-weight control panels at once.

### Typography Over Boxes

Hierarchy should be carried primarily by:

- title scale
- summary vs metadata contrast
- spacing
- restrained use of color

not by:

- a card around every section
- repeated chips
- stacked status blocks
- multiple equally loud headers

### Metadata Must Stay Secondary

Across all surfaces:

- title and summary must outrank counts and labels
- rationale should sit beside the item it explains
- route, confidence, and deeper system detail should default to collapsed or secondary presentation

### Actions Must Be Grouped And Tiered

Each visible region should have:

- at most one obvious primary action cluster
- a small number of secondary actions
- deeper utilities hidden behind selection or disclosure

The interface should guide the user toward the next best action, not present every possible action at once.

### Preview Must Not Compete With Source

For draft-oriented surfaces:

- the source editor remains primary
- rendered preview is optional and conditional
- lifecycle controls stay secondary to the draft body

### Chips Are Tertiary

Proof chips, status chips, and compact grounding labels should behave like annotations.

They should not be enlarged, multiplied, or visually promoted to solve discoverability problems that should be solved through hierarchy.

## Out-Of-Bounds Patterns

Future implementation subagents should treat these as anti-patterns:

- browser-tab metaphors for primary mode switching
- database-row UI for provenance
- always-open multi-column inspection shells in default chat
- equal-weight card stacks for every meaning layer
- new ontology terms introduced only for polish
- bright accent fills or loud gradients on routine controls
- solving density problems by adding more chips, labels, or explanatory copy

## Build Order

The recommended implementation order remains:

1. `Chat`
2. `Whiteboard`
3. `Vantage`
4. `Scenario Lab`
5. shared visual-system tightening

Why:

- `Chat` is the first impression
- `Whiteboard` is the most important premium-authored surface
- `Vantage` should build on stronger global hierarchy
- `Scenario Lab` should inherit a calmer, more intentional inspection language

## Pass 02A: Chat Visual Voice

### Goal

Make the default chat surface feel materially more refined without changing turn semantics.

### User-Visible Outcome

The user should feel that the answer is the product.

The shell, chips, and controls should support the answer rather than compete with it.

### Allowed File Scope

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs) if compact summary wording needs to be centralized

### Disallowed Changes

- no ontology renames
- no new toolbar rows
- no change to grounding truth
- no louder experiment/session chrome

### Visual Rules

- Make the transcript visually dominant over the masthead.
- Keep the header to one title, one supporting sentence, one quiet session row, and one restrained utility cluster.
- Assistant messages should read as the most comfortable long-form text in the app.
- User messages should remain compact and clearly subordinate.
- Evidence chips must stay on a quiet rail beneath the assistant answer, never above it.
- Chip count should stay low; if density grows, solve it in render logic rather than styling.
- The composer should feel like a writing tool, not a boxed settings panel.
- In whiteboard-focused mode, `Chat` should clearly read as a sidebar and not compete with the whiteboard surface.

### Acceptance Criteria

- On first load, the eye lands on the transcript, not the header.
- Assistant answers feel materially more premium and readable than user messages.
- Evidence chips read as annotations rather than the main event.
- Experiment state remains visible but clearly subordinate.
- Whiteboard-related inline notices stay temporary and lightweight.

### Required Checks

- visual sanity check in normal chat mode
- visual sanity check in whiteboard-sidebar mode
- regression check for chip ordering and summary strings if render logic changes

## Pass 02B: Whiteboard Document Surface

### Goal

Make the whiteboard feel like the highest-quality authored surface in the product.

### User-Visible Outcome

When the whiteboard opens, it should feel like a real shared drafting surface rather than an app panel with text inside it.

### Allowed File Scope

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

### Disallowed Changes

- no second editor surface
- no preview promoted to equal weight with the source draft
- no collapsing whiteboard semantics into artifact or Vantage semantics

### Visual Rules

- Frame the whiteboard like a document page inside the app, not like a tool panel.
- Keep the utility bar visually quiet and separate from the page body.
- Make the title deck the strongest block on the page.
- Use a centered authored page with a restrained desktop measure.
- Keep prose line length comfortable and consistent in both editing and rendered states.
- Preserve generous separation between title, lifecycle panels, editor, and preview.
- Keep the source editor primary.
- Keep preview below or behind the draft body unless it materially improves reading of code or math.
- Keep side-chat clearly secondary while whiteboard is active.
- Keep lifecycle and artifact state panels visible but visually quieter than the document body.

### Acceptance Criteria

- The whiteboard reads immediately as the place where shared drafting happens.
- The title area feels editorial and dominant.
- The editor has comfortable document measure and strong markdown readability.
- Preview, when present, supports reading without competing with the source draft.
- The chat sidebar remains usable but clearly secondary.

### Required Checks

- visual sanity check with a plain prose draft
- visual sanity check with code or math preview visible
- state check that lifecycle panels remain present but non-dominant

## Pass 02C: Vantage Guided Narrative

### Goal

Make `Vantage` feel like a layered explanation surface instead of a refined dashboard.

### User-Visible Outcome

Opening `Vantage` should feel like opening a guided provenance review.

The first scan should answer:

- why this answer
- what was in working memory
- what was recalled
- what was learned

Only after that should deeper details appear.

### Allowed File Scope

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs) if section summaries or compact labels are centralized there

### Disallowed Changes

- no renaming of semantic concepts for style
- no implication that inspect-only items were in scope
- no always-open diagnostics wall

### Visual Rules

- Organize the surface top-down as: summary, `This turn`, `Working Memory`, `Recall`, `Learned`, then deeper detail.
- Keep `Reasoning Path` secondary to the main summary.
- Reduce repeated card framing so the page reads like a narrative review rather than a stack of panels.
- Use title-first item treatment for recalled and learned items.
- Attach `Why recalled` and `Saved because` directly to the item they explain.
- Default-collapse route detail, long continuity detail, and deeper correction-path explanation.
- Keep learned items readable as durable outcomes, not system logs.
- Keep the distinction between `Working Memory`, `Recall`, and `Memory Trace` legible.
- Keep `Scenario Lab` visually distinct from ordinary provenance blocks.
- Do not merge `Working Memory` and `Recall` into one unlabeled explanation bucket.

### Acceptance Criteria

- A user can understand the answer provenance in one quick scan.
- Recalled items, learned items, and Scenario Lab each have distinct visual roles.
- `Reasoning Path` is available but clearly secondary.
- The surface feels calmer and more premium without losing truthfulness.

### Required Checks

- visual sanity check on working-memory-grounded turn
- visual sanity check on best-guess turn
- visual sanity check on mixed-context turn with learned material

## Pass 02D: Scenario Lab Flagship Presentation

### Goal

Make Scenario Lab read as a signature reasoning capability rather than just another answer block.

### User-Visible Outcome

The question, comparison hub, recommendation, and branch set should read as one coherent reasoning experience.

### Allowed File Scope

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html) if small structure changes are required

### Disallowed Changes

- no backend-complexity expansion just to create more spectacle
- no mixing Scenario Lab semantics into ordinary evidence cards

### Visual Rules

- Keep the question and recommendation visually central.
- Treat the comparison artifact as the durable anchor for the branch set.
- Make branch cards easy to scan and clearly related to each other.
- Keep reopen and inspect actions present but secondary.
- Keep support rationale visible but demoted.

### Acceptance Criteria

- Scenario Lab reads as a first-class reasoning mode.
- Branch comparison feels clearer than ordinary provenance review.
- The user can quickly reopen or inspect branch details without entering a console-like experience.

### Required Checks

- scenario prompt path renders without errors
- branch reopen and inspect affordances remain clear
- comparison artifact still reads as the hub

## Pass 02E: Shared Visual-System Tightening

### Goal

Make the product feel like one authored system after the surface-specific passes land.

### Allowed File Scope

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- supporting markup or small JS hooks only where needed to maintain consistency

### Visual Rules

- Reduce medium-emphasis colors.
- Make border usage more selective.
- Keep primary, secondary, and tertiary hierarchy consistent across surfaces.
- Use one coherent spacing rhythm.
- Ensure buttons and chips feel intentional and not generic.

### Acceptance Criteria

- The app feels coherent across `Chat`, `Whiteboard`, `Vantage`, and `Scenario Lab`.
- The user can tell the product visually changed.
- The whole app feels calmer and more authored, not louder.

## Verification Expectations

Each implementation pass should include:

- at least one visual sanity-check scenario per affected surface
- relevant frontend tests if render order, disclosure defaults, or compact labeling changed
- any needed codebase docs updates under `docs/codebase/webapp/src/vantage_v5/webapp/`
- a repo hygiene run before closeout

Recommended scenario matrix:

- `Chat`: normal answer, whiteboard-offer answer, whiteboard-sidebar state
- `Whiteboard`: fresh draft, continued draft, draft with preview-worthy code or math
- `Vantage`: best-guess turn, recall-grounded turn, mixed-context turn, learned-item turn
- `Scenario Lab`: successful branch set, reopen or inspect flow, comparison artifact focus

## What Future Subagents Must Not Invent

Subagents implementing from this plan should not invent:

- new semantic terms to make the UI sound nicer
- mutation actions that the backend does not support
- new scope semantics for visible/open/pinned context
- new default surfaces

If a visual pass requires a semantic change, that should be proposed separately as product or architecture work, not slipped into styling.
