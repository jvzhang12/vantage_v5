# UI Research

This folder collects product-design research for making Vantage feel clearer, calmer, and more intuitive without abandoning the current architecture.

The goal is not to copy another product's visual brand.

The goal is to understand the best interaction patterns for:

- chat-first AI
- optional drafting surfaces
- inspectable context and memory
- trustworthy but non-overwhelming transparency

## Read Order

1. [comparable-systems.md](comparable-systems.md)
2. [inspectability-patterns.md](inspectability-patterns.md)
3. [vantage-ui-audit.md](vantage-ui-audit.md)
4. [vantage-ui-direction.md](vantage-ui-direction.md)
5. [external-feedback-action-plan.md](external-feedback-action-plan.md)
6. [frontend-guidance-implementation-plan.md](frontend-guidance-implementation-plan.md)
7. [vantage-refinement-pass-01.md](vantage-refinement-pass-01.md)
8. [vantage-stylistic-direction.md](vantage-stylistic-direction.md)
9. [stylistic-inspiration-elements.md](stylistic-inspiration-elements.md)
10. [vantage-visual-redesign-pass-02.md](vantage-visual-redesign-pass-02.md)

## Active Implementation Docs

If you are deciding what to build next, start here:

1. [../codebase/webapp/README.md](../codebase/webapp/README.md) for current React source targets.
2. [../architecture-overview.md](../architecture-overview.md) for the current frontend serving contract.

Older implementation plans are retired as active trackers. Some remain in this folder for historical context, and the archived checklist is indexed in [archive/README.md](archive/README.md). When they conflict, the current architecture overview and React codebase summaries win.

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
