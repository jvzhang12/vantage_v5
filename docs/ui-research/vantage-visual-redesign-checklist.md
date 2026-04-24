# Vantage Visual Redesign Checklist

This checklist turns Pass 02 into implementation slices tied to the current repository.

It is not the canonical semantics or execution contract by itself.

Implementation subagents should treat [vantage-visual-redesign-master-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-master-plan.md) as the primary build document and use this checklist as the shorter companion view.

It assumes:

- the current surface architecture remains
- the current semantics remain
- the goal is stronger visible product quality, not ontology changes

## Source Docs

This checklist is grounded in:

1. [docs/ui-research/vantage-visual-redesign-pass-02.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-pass-02.md)
2. [docs/ui-research/vantage-refinement-pass-01.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-refinement-pass-01.md)
3. [docs/ui-research/vantage-ui-direction.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)
4. [docs/ui-research/vantage-ui-audit.md](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-audit.md)
5. [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
6. [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
7. [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

## Pass 02A: Rebuild The Chat Visual Voice

Goal:

- make the default chat surface feel materially more refined

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- reduce visible chat chrome further
- make transcript typography noticeably more comfortable
- soften generic message-card feeling
- make assistant answers visually dominant
- keep chips and notices secondary to the answer body

Success criteria:

- a user notices the difference without opening whiteboard or `Vantage`

## Pass 02B: Make Whiteboard Feel Like A Real Document Surface

Goal:

- make whiteboard look like the highest-quality authored surface in the app

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- strengthen page/document framing
- make title area more editorial
- increase separation between draft body and support controls
- keep lifecycle/support information quiet but legible
- make side-chat feel clearly secondary

Success criteria:

- the whiteboard feels like the place where serious shared work happens

## Pass 02C: Turn Vantage Into A Guided Narrative Surface

Goal:

- make `Vantage` feel like a layered explanation instead of a refined dashboard

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- create one clearer narrative spine for `This Turn`
- demote secondary support blocks visually
- rely more on spacing and typography than repeated card framing
- make disclosures feel layered and intentional
- keep deep detail available without leading with it

Success criteria:

- opening `Vantage` feels like opening an explanation, not a control surface

## Pass 02D: Give Scenario Lab A Flagship Presentation

Goal:

- make Scenario Lab feel unmistakably like a signature reasoning capability

Primary files:

- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- strengthen the question/recommendation hierarchy
- make the comparison hub visibly central
- improve branch-card scanability
- make reopen and inspect actions clearer
- keep support rationale present but secondary

Success criteria:

- Scenario Lab feels like a first-class mode, not a specialized panel

## Pass 02E: Tighten The Overall Visual System

Goal:

- make the whole product feel like one authored system rather than improved local parts

Primary files:

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- reduce the number of medium-emphasis colors
- tighten spacing rhythm
- make border usage more selective
- ensure primary / secondary / tertiary hierarchy is consistent across surfaces
- make buttons and chips feel more intentional and less generic

Success criteria:

- the app feels coherent and ship-ready across `Chat`, `Whiteboard`, `Vantage`, and Scenario Lab

Status:

- implemented
- verified with the focused frontend checks
- documented in the webapp codebase notes

## Recommended Build Order

The strongest order is:

1. Pass 02A: Chat visual voice
2. Pass 02B: Whiteboard document surface
3. Pass 02C: Vantage guided narrative
4. Pass 02D: Scenario Lab flagship presentation
5. Pass 02E: overall visual-system tightening

Why:

- chat needs the most obvious first-impression change
- whiteboard is the most important premium surface after chat
- `Vantage` and Scenario Lab should build on a stronger visual foundation

## What To Avoid

- do not rename semantic concepts just to sound more product-like
- do not let styling moves obscure recall or grounding truth
- do not create a louder product by making everything more emphasized
- do not make every surface use the same panel language
- do not keep solving a visual problem with more badges, labels, or explanatory copy

## Acceptance Criteria

Pass 02 is complete when:

- the user can tell at a glance that the product changed
- chat feels premium and readable
- whiteboard feels like the best writing surface
- `Vantage` feels guided and intentional
- Scenario Lab feels flagship
- the whole app feels ready to ship
