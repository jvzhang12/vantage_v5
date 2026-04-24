# External Feedback Follow-On Roadmap

This document captured the remaining implementation work implied by the latest hands-on user feedback after the first external-feedback slice pass.

It exists so the remaining product issues do not get lost behind incremental fixes.

It should be read after:

1. [external-feedback-action-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-action-plan.md)
2. [external-feedback-implementation-slices.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-implementation-slices.md)

## What This Roadmap Is For

The first pass clearly improved:

- recall explanations
- learned-item inspectability
- whiteboard lifecycle clarity
- Vantage tone
- whiteboard preview restraint

But the feedback also identified the next layer of work:

- some terminology is still a little terse or systemy
- learned items still do not feel fully correctable
- Vantage still feels dense even though the language improved
- whiteboard lifecycle copy is clear but sometimes mechanical
- Scenario Lab needs explicit robustness validation after the renderer fix

This roadmap turns those remaining issues into concrete product work.

## Status Snapshot

As of the current implementation pass, the planned follow-on slices in this file have been completed as frontend refinement work:

- Priority 0: complete
- Priority 1: complete as a truthful first-pass UI correction loop, with deeper durable edit / forget mutation still explicitly deferred to backend storage work
- Priority 2: complete
- Priority 3: complete
- Priority 4: complete
- Priority 5: complete
- Priority 6: complete

What remains after this roadmap is no longer copy/hierarchy cleanup. The remaining work is deeper product capability work such as real durable mutation, deletion, or scope changes for learned items.

The latest calm-state refinement pass also closed a smaller but important product layer that came from subsequent user testing:

- reduce stacked toast/noise behavior
- demote experiment controls so they do not compete with primary chat actions
- lighten the first visible layer of Vantage so it reads as a short confidence summary first

Those refinements were implemented without changing the underlying surface model.

## Current Product Read

The current external read is now:

`This feels more like a product and less like a memory demo.`

That means the next passes should not destabilize the current surface model.

We should preserve:

- calm chat
- whiteboard as the collaborative drafting surface
- Vantage as guided inspection
- Recall / Working Memory / Learned / Library semantics

The next work is not another architecture pass.

It is a refinement pass on:

- wording
- hierarchy
- correction affordances
- robustness

## Priority Order

### Priority 0: Keep The Concrete Bug Closed

Status: complete

This is already fixed, and the renderer path remains explicitly tracked.

#### Goal

Prevent Scenario Lab regressions from undermining trust.

#### Work

- keep the `firstNonEmptyString` / branch-roster regression covered
- make sure Scenario Lab render paths continue to use shared normalization helpers instead of local copy logic
- ensure cache-busting stays deliberate after Scenario Lab UI changes

#### Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)
- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)

#### Acceptance

- Scenario Lab prompt paths do not throw in the browser
- branch-roster rendering is normalized through one shared seam
- any Scenario Lab UI hotfix updates cache-busting intentionally

---

### Priority 1: Make Learned Items Fully Correctable

This is the highest-leverage remaining product opportunity.

Status: complete for the current architecture

The feedback was clear:

`Saved because` is good, but the correction loop still does not feel complete.

#### Goal

Make learned-state feel editable, reversible, and scoped.

#### User Outcome

When the system learns something, the user should be able to clearly do one of these:

- keep this
- edit this
- make this temporary
- forget this
- mark this as wrong

#### Product Principle

`Visible, correctable memory` should become concrete interaction, not just messaging.

#### Likely Slices

1. Learned-item action model
2. Scope-change affordances
3. Forget / remove flow
4. Lightweight edit flow

#### Frontend Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

#### Likely Backend Seams

- [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py)
- [src/vantage_v5/services/chat.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/chat.py)
- [src/vantage_v5/services/executor.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/executor.py)
- [src/vantage_v5/storage/markdown_store.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/storage/markdown_store.py)

#### Notes

If true delete/forget is not yet safe at the storage layer, the first pass should still make the correction path explicit in the UI rather than pretending it exists.

That means it is acceptable to stage this in two steps:

1. explicit visible correction affordances
2. full durable mutation/delete support

Current result:

- learned items now expose inspectable `Saved because` and scope state
- the direct action path is explicit and truthful: revise / continue in whiteboard
- pinning now uses the pinned-context contract instead of implying single-turn carry
- unsupported mutation paths are presented as guidance (`How to mark wrong`, `How to make temporary`, `How to forget`) instead of fake action buttons

Deferred follow-on:

- true durable edit / forget / scope mutation remains backend work, not a frontend wording issue

#### Acceptance

- learned items expose clear user actions, not just inspection
- temporary vs durable can be changed or explicitly chosen where architecture allows
- forget/remove behavior is visible and truthful
- the user does not have to infer how to correct a saved item

#### Tests

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)
- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)
- [tests/test_server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/test_server.py)

---

### Priority 2: Humanize The Last Terse Proof Chips

Status: complete

The feedback called out that some chip labels still read as a little internal:

- `Recall`
- `Recent Chat`
- `Recalled now`

#### Goal

Make compact transcript evidence feel more human without losing precision.

#### Design Direction

Prefer phrases that answer:

`What helped with this answer?`

Possible directions:

- `Brought in from earlier`
- `From recent conversation`
- `Used from your draft`
- `Pulled in for this turn`

This should be done carefully.

The chips still need to stay:

- compact
- scannable
- stable across turns

#### Files

- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

#### Acceptance

- transcript chips feel less systemy
- evidence still stays compact
- labels remain truthful across all grounding cases

#### Tests

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)

---

### Priority 3: Tighten Whiteboard Lifecycle Copy

Status: complete

The latest pass made whiteboard state much clearer, but some phrases still sound implementation-aware.

#### Goal

Keep the trust win while making the language feel more natural.

#### Target Areas

- start fresh draft
- continue current draft
- reuse prior material into draft
- accepted draft pulled into the whiteboard

#### Design Direction

Prefer copy that sounds like collaborative writing, not state reconciliation.

Examples:

- `Updated your draft with this turn’s changes`
- `Continued your draft using the latest request`
- `Started a new draft from earlier work`

#### Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/whiteboard_decisions.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/whiteboard_decisions.mjs)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)

#### Acceptance

- the user can tell what happened to the whiteboard immediately
- the wording sounds like drafting help, not system mechanics
- destructive-replacement risk remains explicit where needed

#### Tests

- [tests/webapp_whiteboard_decisions.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_whiteboard_decisions.test.mjs)
- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)

---

### Priority 4: Reduce Vantage Density And Improve Hierarchy

Status: complete

The vocabulary is now much better.

The remaining problem is layout hierarchy.

#### Goal

Move Vantage from:

- good provenance vocabulary

to:

- guided confidence review

#### Product Direction

The Vantage reading order should become more obviously layered:

1. strongest summary
2. what actually mattered
3. what changed
4. deeper inspection on demand

#### Concrete UI Moves

1. Compress the default visible card stack
2. Reduce chip density in the default state
3. Push more metadata into expandable rows
4. Make `Reasoning Path` even more secondary relative to the summary
5. Visually separate:
   - answer summary
   - support
   - learned changes
   - library

#### Files

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)

#### Acceptance

- default Vantage view feels lighter
- strongest turn summary dominates visually
- deeper detail is still available but not equally loud
- users can describe the surface as review, not inspection tooling

---

### Priority 5: Validate Whiteboard Preview For Math And Code

Status: complete

The latest feedback confirms the preview is no longer noisy for normal drafts.

We still need to validate the positive case.

#### Goal

Make sure the preview appears only when useful, and works well when it does appear.

#### Validation Paths

- whiteboard draft with LaTeX-style math
- whiteboard draft with fenced code
- mixed prose + code
- mixed prose + math

#### Files

- [src/vantage_v5/webapp/math_render.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/math_render.mjs)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

#### Acceptance

- no preview for ordinary prose drafts
- preview appears reliably for math/code drafts
- preview styling feels like a helpful read surface, not a debug panel

Completion note:

- the preview gate is now centralized through `deriveWhiteboardPreviewState()`
- regression coverage now explicitly checks prose-hidden, math-visible, code-visible, and mixed-content-visible behavior

#### Tests

- [tests/math_render.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/math_render.test.mjs)

---

### Priority 6: Scenario Lab Confidence And Identity Review

Status: complete

Once the renderer bug is closed, Scenario Lab should get one explicit experience-validation pass.

#### Goal

Confirm that Scenario Lab reads as:

- a first-class reasoning mode
- distinct from ordinary Vantage provenance
- calm rather than overconfident

#### Validation Questions

- does the route into Scenario Lab feel intentional?
- does the recommendation lead the experience clearly?
- do branch actions feel obvious?
- does confidence language feel helpful rather than false-precision?

#### Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

#### Acceptance

- Scenario Lab is stable in the browser
- recommendation and branch structure are clear
- confidence language feels qualitatively useful
- Scenario Lab still feels like a differentiator

Completion note:

- the Scenario Lab hero now uses qualitative route-fit language instead of awkward adjective-only copy
- branch cards now soften branch-level confidence wording so the mode reads as comparison guidance, not false precision

## Sequence Used

The implementation sequence completed from this roadmap was:

1. Learned-item correction loop
2. Whiteboard lifecycle copy tightening
3. Humanize terse proof chips
4. Vantage hierarchy / density pass
5. Whiteboard preview positive-case validation
6. Scenario Lab product validation pass

## Why This Sequence

This order preserves product momentum:

- trust first
- clarity second
- polish third
- validation after changes land

It also matches the current repository seams.

The next highest-value work is not another broad redesign.

It is finishing the parts of the current design that users still experience as:

- slightly mechanical
- slightly dense
- not fully correctable

## Tracking Rule

This roadmap should be updated when:

- a listed priority changes from complete to reopened
- acceptance criteria materially change
- the next round of real-user testing reveals a better ordering

It should not be left as a frozen brainstorm document.

It is meant to be used as the active follow-on implementation queue for the remaining external-feedback product work.
