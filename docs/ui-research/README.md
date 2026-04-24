# UI Research

This folder collects product-design research for making Vantage feel clearer, calmer, and more intuitive without abandoning the current architecture.

The goal is not to copy another product's visual brand.

The goal is to understand the best interaction patterns for:

- chat-first AI
- optional drafting surfaces
- inspectable context and memory
- trustworthy but non-overwhelming transparency

## Read Order

1. [comparable-systems.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/comparable-systems.md)
2. [inspectability-patterns.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/inspectability-patterns.md)
3. [vantage-ui-audit.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-audit.md)
4. [vantage-ui-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-ui-direction.md)
5. [external-feedback-action-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-action-plan.md)
6. [external-feedback-implementation-slices.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-implementation-slices.md)
7. [external-feedback-follow-on-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-follow-on-roadmap.md)
8. [vantage-refinement-pass-01.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-refinement-pass-01.md)
9. [vantage-stylistic-direction.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-stylistic-direction.md)
10. [stylistic-inspiration-elements.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/stylistic-inspiration-elements.md)
11. [vantage-visual-redesign-pass-02.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-pass-02.md)
12. [vantage-visual-redesign-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-checklist.md)
13. [vantage-visual-redesign-master-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-master-plan.md)

## Active Implementation Docs

If you are deciding what to build next, start here:

1. [vantage-visual-redesign-master-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-master-plan.md)
2. [external-feedback-implementation-slices.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-implementation-slices.md)
3. [external-feedback-follow-on-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-follow-on-roadmap.md)

Older implementation checklists have been moved into [archive/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/archive/README.md) so this folder stays easier to scan.

## Core Thesis

Across the strongest comparable products, the winning pattern is:

- keep ordinary chat calm
- move durable work into an explicit adjacent surface
- keep project or source boundaries legible
- keep deep inspection available, but secondary

For Vantage, that suggests:

- `Chat` should stay the obvious home screen
- `Whiteboard` should feel like the one active drafting surface
- `Vantage` should feel like guided inspection, not an operator console
- `Library` should stay inside `Vantage`
- `Reasoning Path` should stay available, but collapsed behind a turn-level summary

The later Pass 02 redesign docs build on this foundation, but raise the bar from:

- calmer and cleaner

to:

- visibly differentiated
- more opinionated
- ready to ship

## Scope

This research bundle is grounded in:

- Vantage repository semantics as of April 21, 2026
- official/public product documentation for comparable systems where available
- a local audit of the current Vantage UI structure and terminology
