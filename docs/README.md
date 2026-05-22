# Vantage Docs Guide

> Status: Current source of truth
> Note: This is the tracked entrypoint for choosing current, historical, compatibility, and local-state documentation. Local untracked brainstorm or assessment docs are context inputs only until explicitly tracked.

This is the best starting point for the repository documentation.

Use this guide when you want to know:

- what Vantage means today
- which docs are current
- where to start for implementation work
- where UI planning lives
- where older plans were archived

## Start Here

If you are orienting to the current product, read in this order:

1. [README.md](../README.md)
2. [architecture-overview.md](architecture-overview.md)
3. [glossary.md](glossary.md)
4. [semantic-rules.md](semantic-rules.md)
5. [implementation-vs-canon.md](implementation-vs-canon.md)
6. [codebase/README.md](codebase/README.md)

That sequence gives you:

- current product truth
- current runtime architecture
- canonical repo vocabulary
- implementation-facing behavior rules
- current repo versus older canon clarification
- a map of the actual code

## By Task

### Product Semantics

Use these when you are changing user-facing behavior or trying to preserve canonical terminology:

- [glossary.md](glossary.md)
- [semantic-rules.md](semantic-rules.md)
- [working-memory-and-trace-model.md](working-memory-and-trace-model.md)
- [reasoning-path.md](reasoning-path.md)
- [navigator-continuity-contract.md](navigator-continuity-contract.md)
- [control-panel-navigation.md](control-panel-navigation.md)
- [protocols.md](protocols.md)
- [semantic-frame.md](semantic-frame.md)

### Implementation Planning

Use these for active implementation work:

- [system-improvements-checklist.md](system-improvements-checklist.md)
- [system-improvements-assessment.md](system-improvements-assessment.md)
- [conversation-continuity-resume-todo.md](conversation-continuity-resume-todo.md)
- [whiteboard-draft-retention-todo.md](whiteboard-draft-retention-todo.md)
- [refactor-deep-modules-plan.md](refactor-deep-modules-plan.md)
- [architecture-overview.md](architecture-overview.md)
- [subagent-orchestration-protocol.md](subagent-orchestration-protocol.md)
- [codebase/README.md](codebase/README.md)

The older current-repo implementation roadmap has been archived at [archive/implementation-roadmap.md](archive/implementation-roadmap.md). Use it for historical context only; active implementation direction should come from the current product docs, architecture overview, codebase maps, and the active lane handoff.

Current status note:

- `answer_basis` badges and protocol/evidence separation are implemented, but the broader Inspect consolidation remains ongoing.
- `learned` remains the API field for turn-created or turn-saved records; UI copy may present the same review surface as `Saved for Later`.
- Saved for Later supports `Hide as incorrect` and `Don't use again` as hide/suppress corrections, not hard deletes. Direct edit, hard delete, make-temporary, freshness, and confidence actions remain deferred until their semantics are explicit.

### Deployment

Use this when preparing private hosted access, Docker, Basic Auth, or persistent storage:

- [deployment.md](deployment.md)

### Compatibility And Local State

Use these when a field, path, or local artifact looks stale but may still have a compatibility reason:

- [compatibility-ledger.md](compatibility-ledger.md)
- [stale-artifact-inventory.md](stale-artifact-inventory.md)
- [stale-code-inventory.md](stale-code-inventory.md)
- [repository-entropy-audit.md](repository-entropy-audit.md)

Local files such as `docs/brainstorm.md`, `docs/brainstorm-implementation-list.md`, `docs/vantage-behavioral-workflow-canon.md`, and `docs/behavioral-workflow-assessment-2026-05-21.md` may exist untracked in this worktree. If untracked, treat them as local assessment or brainstorm inputs, not current product contracts.

### UI Research And Frontend Direction

Use these when the task is about UX, product framing, or frontend implementation slices:

- [ui-research/README.md](ui-research/README.md)
- [codebase/webapp/README.md](codebase/webapp/README.md) for current React implementation targets.

Older UI implementation plans remain useful historical rationale, but many predate the React-only frontend transition. Follow their status headers when deciding whether a file is current guidance.

### Historical Or Deferred Plans

Use these only when you need historical rationale or a deferred architecture thread:

- [archive/README.md](archive/README.md)
- [archive/implementation-roadmap.md](archive/implementation-roadmap.md)
- [archive/implementation-plans/README.md](archive/implementation-plans/README.md)
- [ui-research/archive/README.md](ui-research/archive/README.md)

## Current Active Path

If you want the shortest current path for implementation decisions, use:

1. [README.md](../README.md)
2. [architecture-overview.md](architecture-overview.md)
3. [glossary.md](glossary.md)
4. [semantic-rules.md](semantic-rules.md)
5. [codebase/webapp/README.md](codebase/webapp/README.md)
6. [subagent-orchestration-protocol.md](subagent-orchestration-protocol.md)

## Practical Rule

When in doubt:

- use docs in the main `docs/` folder for current truth
- use `docs/ui-research/` for active UI direction
- use `docs/archive/` only for history

If a document in the archive conflicts with the current repo docs or code, current repo truth wins.
