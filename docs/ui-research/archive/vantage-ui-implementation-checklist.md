# Vantage UI Implementation Checklist

This document turns the UI research bundle into an implementation-facing checklist tied to the current repository.

It is not a redesign brief.

It is a practical build sequence for making Vantage feel calmer, more elegant, and more product-grade while preserving the current architecture:

- chat-first
- whiteboard as the active drafting surface
- Vantage as guided inspection
- Scenario Lab as a distinct reasoning mode

## Source Docs

This checklist is grounded in:

1. [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
2. [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)
3. [docs/semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md)
4. [docs/ui-research/vantage-ui-audit.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-audit.md)
5. [docs/ui-research/vantage-ui-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)
6. [docs/ui-research/vantage-refinement-pass-01.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-refinement-pass-01.md)

If this checklist ever conflicts with the current repo behavior, current repo behavior wins.

## Current Repo Mapping

The current UI already has the right major architectural split.

### Shell and Surface Ownership

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
  - defines the three major surfaces: chat, whiteboard, and Vantage
  - mounts the chat transcript and composer
  - mounts the whiteboard panel
  - mounts Vantage docks for `What Influenced This Response?`, `Scenario Lab`, and `Library`

- [src/vantage_v5/webapp/surface_state.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/surface_state.mjs)
  - is the canonical surface enum and transition helper layer
  - should remain the source of truth for chat vs whiteboard vs Vantage visibility

### Render Orchestration

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
  - is the main orchestration file for:
    - chat transcript rendering
    - evidence chips
    - whiteboard lifecycle and decisions
    - Vantage turn rendering
    - Scenario Lab rendering
    - library inspection actions

### Truthful Labels and Payload Mapping

- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)
  - is the correct place for user-facing evidence and guided-inspection wording

- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)
  - is the canonical payload-normalization layer for:
    - `response_mode`
    - grounding sources
    - recall counts
    - learned items
    - Scenario Lab payload shapes

### Visual System

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
  - already holds the visual direction for:
    - the paper-forward palette
    - shell layout
    - dock styling
    - message cards
    - whiteboard/editor treatment
    - Scenario Lab summary cards

This means the next pass should refine hierarchy and visual weight, not invent a new frontend architecture.

## Implementation Principles

### One Dominant Surface At A Time

- `Chat` is primary by default.
- `Whiteboard` is primary when drafting is active.
- `Vantage` is primary when the user opens guided inspection.

No secondary panel should visually compete with the active surface.

### Semantics Stay In Data/Identity Modules

- Labels and explanatory copy should come from `product_identity.mjs` and `turn_payloads.mjs`.
- `app.js` should orchestrate layout and rendering, not become a second ontology layer.
- `styles.css` should change emphasis and density, not invent meaning.

### Outcome First, Mechanism Second

The UI should show:

1. what the assistant said
2. what influenced it
3. what changed

Only then should it expose:

- candidate context
- full reasoning path detail
- deeper inspection controls

### Whiteboard Decisions Belong In One Place

If the whiteboard is open, drafting decisions belong there.

If the whiteboard is closed, chat can show one compact invitation or draft-ready cue.

`Vantage` should inspect those decisions, not compete with them.

## Implementation Waves

### Pass 01A: Calm The Shell

Goal:

- reduce the feeling of a multi-panel prototype
- make the active surface visually obvious

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/surface_state.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/surface_state.mjs)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)

Checklist:

- Make the chat header lighter and less control-heavy.
- Reduce perceived chrome around the transcript and composer.
- Ensure the current shell class makes the active surface visually dominant without needing extra notices.
- Make `shell--whiteboard` feel like a drafting mode, not like chat with another panel attached.
- Keep `shell--vantage` clearly inspection-focused instead of looking like a second dashboard.

Tests and verification:

- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)
- manual verification of:
  - chat default load
  - whiteboard open / close
  - Vantage open / close
  - return-surface behavior after refresh

Risk:

- broad shell edits can accidentally regress surface return behavior or make whiteboard and Vantage compete visually again

### Pass 01B: Make Whiteboard Feel Premium

Goal:

- make the whiteboard feel like the best surface in the product when active

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/workspace_state.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/workspace_state.mjs)

Checklist:

- Treat the whiteboard header more like an editorial workspace header and less like a control bar.
- Center the document more clearly inside the whiteboard surface.
- Reduce visual competition between lifecycle cues and the actual draft text.
- Keep save / save-as-artifact actions available but quieter.
- Keep the chat sidebar usable while clearly secondary.
- Ensure whiteboard-side decisions appear there, not duplicated elsewhere as competing notices.

Tests and verification:

- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)
- [tests/webapp_whiteboard_decisions.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_whiteboard_decisions.test.mjs)
- manual verification of:
  - draft-ready whiteboard
  - saved whiteboard
  - promoted artifact cue
  - replace / append / keep-current decision states

Risk:

- styling simplification can accidentally hide important lifecycle truth or make the whiteboard feel visually inert

### Pass 01C: Refactor Vantage Into A Stronger This-Turn Hierarchy

Goal:

- make Vantage read as guided inspection instead of many sibling cards

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)

Checklist:

- Reframe the top answer dock as `This Turn` in presentation, even if internal payload semantics still use `Working Memory`.
- Put the short answer summary and compact grounding summary first.
- Keep `Recall`, `Memory Trace`, and `Learned` as subordinate parts of one explanation instead of equal-weight sibling frames.
- Collapse `Reasoning Path` by default.
- Move candidate-context or deep inspection details behind explicit disclosure.
- Keep `Library` and `Scenario Lab` visible, but secondary to the primary turn explanation.

Tests and verification:

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)
- manual verification of:
  - working-memory grounded turn
  - whiteboard grounded turn
  - true best-guess turn
  - learned-item turn

Risk:

- over-aggressive reheading can blur the difference between `Working Memory` as a real internal concept and `This Turn` as a calmer presentation layer

### Pass 01D: Reduce Metadata Density In Chat

Goal:

- keep chat truthful without making badges and notices compete with the answer

Primary files:

- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)
- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- Keep compact chat evidence, but reduce the number of simultaneously emphasized chips.
- Reserve stronger tones for truly important states:
  - `Scenario Lab`
  - durable `Learned`
  - `Best Guess`
- Demote lower-priority labels into quieter styling.
- Avoid repeating the same whiteboard state in transcript, chat notice, and Vantage at the same time.
- Keep product-facing grounding names stable through `product_identity.mjs`, not ad hoc in render code.

Tests and verification:

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)

Risk:

- if the frontend starts compressing too aggressively without the truth layer guiding it, Vantage will under-explain or mislabel grounding

### Pass 01E: Give Scenario Lab A Distinct Premium Identity

Goal:

- make Scenario Lab feel like a distinct reasoning mode, not just another card group inside Vantage

Primary files:

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

Checklist:

- Keep the comparison question and recommendation visually central.
- Make branch assumptions, risks, and reopen actions easier to scan.
- Use the comparison artifact as the durable revisit hub in presentation.
- Distinguish Scenario Lab visually from ordinary answer inspection through spacing, tone, and section treatment rather than louder chrome.
- Avoid making Scenario Lab feel like a console or a separate product bolted on top.

Tests and verification:

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)
- backend assertions remain in [tests/test_server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/test_server.py)

Risk:

- if Scenario Lab reuses the exact same visual treatment as ordinary turn inspection, it loses its product identity

## Recommended Build Order

The safest order is:

1. wording and label cleanup in `product_identity.mjs` and `turn_payloads.mjs`
2. render hierarchy cleanup in `app.js` and `index.html`
3. visual-system refinement in `styles.css`
4. only then smaller follow-up adjustments for Scenario Lab and dock structure

That keeps semantics truthful while reducing the risk of styling around unstable copy or unstable hierarchy.

## Recommended First Implementation Slice

If we implement this in waves, the strongest next slice is:

### Slice 1

- Pass 01A: Calm The Shell
- Pass 01B: Make Whiteboard Feel Premium

Why:

- this produces the biggest visible change in product quality
- it stays closest to the user’s current complaints about clutter and prototype feel
- it does not require deeper Vantage re-architecture yet

After that, the next slice should be:

### Slice 2

- Pass 01C: Refactor Vantage Into A Stronger This-Turn Hierarchy
- Pass 01D: Reduce Metadata Density In Chat

Then:

### Slice 3

- Pass 01E: Give Scenario Lab A Distinct Premium Identity

## What Not To Do In This Pass

- do not introduce a frontend framework migration
- do not rename backend `workspace_*` contracts as part of visual refinement
- do not move semantic truth out of `turn_payloads.mjs` / `product_identity.mjs` into ad hoc render logic
- do not make Vantage the default home surface
- do not make whiteboard, Vantage, and chat equally loud at the same time

## Acceptance Criteria

This refinement plan is succeeding when:

- chat feels calmer and lighter
- the active whiteboard feels like the best surface in the app
- Vantage reads as guided inspection instead of a dashboard
- Scenario Lab feels distinct without becoming heavier
- evidence stays truthful but visually secondary
- the product no longer feels like many honest cards competing for attention
