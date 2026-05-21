# Codebase Maps

> Status: Current source of truth
> Note: This is the current source/test summary map. Historical generated assessments should not outrank these mirrored summaries.

This directory is the repo's human-first code map.

Use it to understand the implementation before opening large source files directly.

## Read Order

1. Read [README.md](../../README.md) for the current product/runtime contract.
2. Read [docs/architecture-overview.md](../architecture-overview.md) for the current request path, storage model, Navigator/control-panel split, protocol layer, and frontend surfaces.
3. Read [AGENTS.md](../../AGENTS.md) for repo rules.
4. Read [docs/subagent-orchestration-protocol.md](../subagent-orchestration-protocol.md) if you are about to split work across implementation or review subagents.
5. Read the map that matches the layer you plan to edit.
6. Read the mirrored summary for each concrete file you touch.
7. Only then drill into implementation details.

## Orchestration

If you are assigning scoped implementation or review workers, use [docs/subagent-orchestration-protocol.md](../subagent-orchestration-protocol.md) as the execution contract.

It defines the required reading order, scope boundaries, implementation duties, review duties, and closeout expectations for this repository.

## Maps

- [python/README.md](python/README.md)
- [webapp/README.md](webapp/README.md)

## Hygiene Rule

If a source or test file changes, its mirrored summary should move with it in the same edit.

For a quick structural check, run:

```bash
python3 scripts/check_repo_hygiene.py
```
