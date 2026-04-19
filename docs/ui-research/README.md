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

## Scope

This research bundle is grounded in:

- Vantage repository semantics as of April 19, 2026
- official/public product documentation for comparable systems where available
- a local audit of the current Vantage UI structure and terminology
