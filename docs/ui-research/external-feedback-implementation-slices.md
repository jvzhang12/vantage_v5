# External Feedback Implementation Slices

This document translates the external product feedback into a ranked implementation sequence tied to the current frontend architecture.

It is intentionally narrower than the broader UI roadmap.

Its purpose is to answer:

`What should we build next, in what order, and in which files, if we want Vantage to feel more trustworthy and self-explanatory?`

## Completion Snapshot

The ranked slices in this document have now been implemented as frontend refinement work.

Completed in code:

1. `Why Recalled`
2. Inspectable Learned Items
3. Whiteboard Entry Mode Clarity
4. Reframe Vantage Around Provenance
5. Soften The Ontology In Product Language
6. Secondary Visual Polish

The remaining work after this document is no longer slice-definition work. It is deeper capability work such as durable learned-item mutation, deletion, or storage-scope changes where the current backend does not yet expose truthful direct actions.

## Source Documents

This slice list is grounded in:

1. [external-feedback-action-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-action-plan.md)
2. [vantage-ui-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)
3. [vantage-ui-implementation-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/archive/vantage-ui-implementation-checklist.md) (archived background)
4. [docs/codebase/webapp/src/vantage_v5/webapp/app.js.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/app.js.md)
5. [docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md)
6. [docs/codebase/webapp/src/vantage_v5/webapp/turn_payloads.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_payloads.mjs.md)
7. [docs/codebase/webapp/src/vantage_v5/webapp/index.html.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/index.html.md)
8. [docs/codebase/webapp/src/vantage_v5/webapp/styles.css.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/styles.css.md)

## Working Assumption

The current system already has the right major product primitives:

- calm chat
- on-demand whiteboard
- Vantage as guided inspection
- compact proof chips
- structured Recall, Working Memory, Learned, and Library semantics

So the next implementation passes should not introduce a new frontend architecture.

They should clarify and refine the existing one.

## Ranking Logic

These slices are ranked by the expected product payoff relative to implementation disruption.

The main scoring logic is:

1. trust improvements first
2. clarity of surface boundaries second
3. polished framing third
4. broader visual refinement after the truth layer is stronger

## Slice 1: `Why Recalled`

### Why This Comes First

This is the highest-leverage trust improvement from the feedback.

It answers the most important missing question:

`Why did this item come back now?`

Without this, Vantage can show recall, but not yet explain recall.

### User Outcome

Every recalled item shown in Vantage should include a plain-language rationale such as:

- same project
- same trip
- recent whiteboard work
- repeated preference
- related reusable concept

### Primary Frontend Files

- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

### Supporting Truth/Normalization Files

- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

### Likely Backend Follow-On

If the frontend cannot derive a truthful reason from current payloads, the next seam is:

- [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py)
- [src/vantage_v5/services/vetting.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/vetting.py)
- [src/vantage_v5/services/search.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/search.py)

But the first implementation pass should try to keep the change frontend-shaped and payload-light.

### Acceptance Criteria

- every visible recalled item has a one-line reason
- reasons are specific and user-facing
- reasons do not read like internal search telemetry
- chat stays calm; the richer rationale belongs mainly in Vantage

### Tests

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)

## Slice 2: Inspectable Learned Items

### Why It Is Second

The `Learned 1 concept` chip currently creates interest but also uncertainty.

This slice turns learned-state from:

- system did something

into:

- system did something inspectable and correctable

### User Outcome

When something is learned, the user can open a card and see:

- title
- type
- summary/card
- why it was saved
- durable or temporary scope
- actions such as keep, edit, forget

### Primary Frontend Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)

### Supporting Truth/Normalization Files

- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

### Likely Backend Follow-On

If the current learned payload does not include enough rationale/scope truth, the next seam is:

- [src/vantage_v5/services/meta.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/meta.py)
- [src/vantage_v5/services/executor.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/executor.py)
- [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py)

### Acceptance Criteria

- `Learned` always leads to an inspect path
- the user can tell exactly what was saved
- temporary vs durable is legible
- there is an obvious correction path

### Tests

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)
- [tests/test_server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/test_server.py)

## Slice 3: Whiteboard Entry Mode Clarity

### Why It Is Third

The whiteboard already feels promising, but the feedback identified one of the most important remaining trust seams:

users cannot always tell whether the system:

- started a fresh draft
- continued the current draft
- reused saved material into a new draft

### User Outcome

Whiteboard entry should always communicate the mode clearly.

Suggested product phrases:

- `Started a new draft`
- `Continued your current draft`
- `Started a new draft using prior material`

### Primary Frontend Files

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/whiteboard_decisions.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/whiteboard_decisions.mjs)
- [src/vantage_v5/webapp/workspace_state.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/workspace_state.mjs)

### Supporting Truth/Normalization Files

- [src/vantage_v5/webapp/turn_payloads.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/turn_payloads.mjs)

### Likely Backend Follow-On

- [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py)
- [src/vantage_v5/services/navigator.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/services/navigator.py)

This is where explicit mode/source truth may need to be surfaced more directly.

### Acceptance Criteria

- whiteboard opening behavior is explainable on sight
- reuse of prior saved material is visible
- continuing the current draft does not feel like silent replacement

### Tests

- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)
- [tests/webapp_whiteboard_decisions.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_whiteboard_decisions.test.mjs)

## Slice 4: Reframe Vantage Around Provenance

### Why It Is Fourth

This slice is essential, but it should follow after the trust primitives above are stronger.

Otherwise, we risk relabeling the inspection surface without giving it better underlying explanations.

### User Outcome

The Vantage surface should read less like a system console and more like a guided explanation layer.

Suggested section framing:

- `Why this answer`
- `What I used`
- `What I learned`
- `What’s in your library`

### Primary Frontend Files

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)

### Acceptance Criteria

- first glance at Vantage feels human-facing
- `Reasoning Path` still exists, but does not dominate
- Vantage can be described as provenance, not internals

### Tests

- [tests/product_identity.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/product_identity.test.mjs)

## Slice 5: Soften The Ontology In Product Language

### Why It Is Fifth

The feedback does not suggest changing the internal model.

It suggests softening how the internal model is described to normal users.

This should be done after the more concrete trust and provenance flows above, not before.

### User Outcome

Users should more easily understand:

- `Memory` = something to remember
- `Artifact` = work you made
- `Concept` = reusable insight

without needing to learn the full system ontology.

### Primary Frontend Files

- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)

### Supporting Documentation

- [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
- [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)

### Acceptance Criteria

- user-facing copy is simpler than internal architecture language
- internal semantics remain intact
- the product teaches usage, not ontology

## Slice 6: Secondary Visual Polish

### Why It Is Last

The feedback was clear that the product already has real substance.

The next risk is not lack of capability.

It is lack of trust and legibility.

That means broader visual polish should follow, not precede, the explanation and control improvements above.

### User Outcome

Once trust and provenance are stronger, the remaining visual work can make Vantage feel:

- calmer
- more refined
- more premium

without masking unclear behavior.

### Primary Frontend Files

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)

## Recommended Near-Term Execution Order

If we want a practical next sequence:

1. `Why Recalled`
2. Inspectable Learned Items
3. Whiteboard Entry Mode Clarity
4. Vantage Provenance Reframing
5. Ontology Softening
6. Secondary Visual Polish

## Decision Rule

For future frontend work, prefer the slice that most improves this sentence:

`Vantage chats naturally, remembers structurally, and lets the user inspect and shape that continuity.`

If a change makes the product more impressive but less understandable, it should drop in priority.
