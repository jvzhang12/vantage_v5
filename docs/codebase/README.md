# Codebase Maps

This directory is the repo's human-first code map.

Use it to understand the implementation before opening large source files directly.

## Read Order

1. Read [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md) for the current product/runtime contract.
2. Read [AGENTS.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/AGENTS.md) for repo rules.
3. Read [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) if you are about to split work across implementation or review subagents.
4. Read the map that matches the layer you plan to edit.
5. Read the mirrored summary for each concrete file you touch.
6. Only then drill into implementation details.

## Orchestration

If you are assigning scoped implementation or review workers, use [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) as the execution contract.

It defines the required reading order, scope boundaries, implementation duties, review duties, and closeout expectations for this repository.

## Maps

- [python/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/README.md)
- [webapp/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/README.md)

## Hygiene Rule

If a source or test file changes, its mirrored summary should move with it in the same edit.

For a quick structural check, run:

```bash
python3 scripts/check_repo_hygiene.py
```
