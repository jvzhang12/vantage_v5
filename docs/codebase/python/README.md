# Python Codebase Summaries

This directory mirrors the Python source tree and repo Python tooling/tests with one Markdown summary per `.py` file.

The goal is to let future agents understand the codebase shape, responsibilities, and main data flows without reading each implementation file first.

## How To Use This

- Start from [../README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md) if you are not sure which layer you need.
- Start here for a map of the backend.
- Open the summary that matches the file you are about to edit.
- Use the summary to decide whether you need the real code, then drill into the source only when necessary.

## Runtime And API

- [src/vantage_v5/config.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/config.py.md)
- [src/vantage_v5/server.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/server.py.md)

## Services

- [src/vantage_v5/services/chat.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/chat.py.md)
- [src/vantage_v5/services/executor.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/executor.py.md)
- [src/vantage_v5/services/meta.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/meta.py.md)
- [src/vantage_v5/services/navigator.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/navigator.py.md)
- [src/vantage_v5/services/response_mode.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/response_mode.py.md)
- [src/vantage_v5/services/scenario_lab.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/scenario_lab.py.md)
- [src/vantage_v5/services/search.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/search.py.md)
- [src/vantage_v5/services/vetting.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/vetting.py.md)

## Storage

- [src/vantage_v5/storage/artifacts.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/artifacts.py.md)
- [src/vantage_v5/storage/concepts.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/concepts.py.md)
- [src/vantage_v5/storage/experiments.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/experiments.py.md)
- [src/vantage_v5/storage/markdown_store.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/markdown_store.py.md)
- [src/vantage_v5/storage/memory_trace.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/memory_trace.py.md)
- [src/vantage_v5/storage/memories.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/memories.py.md)
- [src/vantage_v5/storage/state.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/state.py.md)
- [src/vantage_v5/storage/vault.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/vault.py.md)
- [src/vantage_v5/storage/workspaces.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/storage/workspaces.py.md)

## Memory Trace Slice

- `memory_trace.py` now implements the first markdown-backed recent-history store that sits alongside the existing JSON debug traces under `traces/`.
- Recent trace items can feed Recall as `memory_trace` candidates without being folded into the durable Library endpoints.

## Tests

- [tests/test_repo_hygiene.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_repo_hygiene.py.md)
- [tests/test_search.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_search.py.md)
- [tests/test_server.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_server.py.md)

## Scripts

- [scripts/check_repo_hygiene.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/scripts/check_repo_hygiene.py.md)
