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
- [src/vantage_v5/services/context_engine.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/context_engine.py.md)
- [src/vantage_v5/services/context_sources.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/context_sources.py.md)
- [src/vantage_v5/services/context_support.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/context_support.py.md)
- [src/vantage_v5/services/draft_artifact_lifecycle.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/draft_artifact_lifecycle.py.md)
- [src/vantage_v5/services/executor.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/executor.py.md)
- [src/vantage_v5/services/local_semantic_actions.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/local_semantic_actions.py.md)
- [src/vantage_v5/services/meta.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/meta.py.md)
- [src/vantage_v5/services/navigator.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/navigator.py.md)
- [src/vantage_v5/services/protocol_engine.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/protocol_engine.py.md)
- [src/vantage_v5/services/protocols.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/protocols.py.md)
- [src/vantage_v5/services/record_cards.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/record_cards.py.md)
- [src/vantage_v5/services/response_mode.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/response_mode.py.md)
- [src/vantage_v5/services/scenario_lab.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/scenario_lab.py.md)
- [src/vantage_v5/services/search.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/search.py.md)
- [src/vantage_v5/services/semantic_frame.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/semantic_frame.py.md)
- [src/vantage_v5/services/semantic_policy.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/semantic_policy.py.md)
- [src/vantage_v5/services/turn_orchestrator.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/turn_orchestrator.py.md)
- [src/vantage_v5/services/turn_payloads.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/turn_payloads.py.md)
- [src/vantage_v5/services/vetting.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/vetting.py.md)
- [src/vantage_v5/services/whiteboard_routing.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/src/vantage_v5/services/whiteboard_routing.py.md)

## Current Backend Flow

- `server.py` owns the HTTP seam, auth/profile runtime selection, experiment/durable store selection, and route registration. The chat-turn lifecycle is delegated to `turn_orchestrator.py`, context preparation is delegated to `context_engine.py`, protocol action resolution is delegated to `protocol_engine.py`, draft/artifact lifecycle operations are delegated to `draft_artifact_lifecycle.py`, and final response compatibility/safe-state shaping is centralized in `turn_payloads.py`.
- `navigator.py` is the model-backed interpreter. Its `control_panel` is the target path for user-intent decisions; deterministic code should execute validated actions rather than re-sort broad intent from raw text.
- `protocols.py` owns reusable task guidance and protocol record helpers. Protocols can be learned/recalled by the protocol interpreter or applied by Navigator `apply_protocol` actions before vetting.
- `protocol_engine.py` validates Navigator `apply_protocol` actions into a typed `ResolvedTurnProtocols` object before Chat or Scenario Lab receive applied protocol kinds, and owns protocol API catalog/update semantics.
- `draft_artifact_lifecycle.py` owns saved-item reopen, whiteboard snapshot saves, visible-whiteboard publish, workspace save snapshots, promotion of saved or unsaved whiteboard buffers into artifacts, and artifact lifecycle card enrichment.
- `record_cards.py` owns UI-facing record-card DTOs for concepts, protocols, saved notes, vault notes, lineage, scenario metadata, and grouped memory payloads.
- `context_engine.py` prepares a single `PreparedTurnContext`: runtime/session, whiteboard scope, redacted or overlaid whiteboard document, pinned context, pending whiteboard carry state, entry mode, and Navigator continuity.
- `context_sources.py` resolves pinned-context summaries, whiteboard source summaries, and Navigator continuity frames from active/durable stores, vault notes, Memory Trace, and recent whiteboards.
- `context_support.py` owns pure workspace-scope, live-buffer, redaction, pending-whiteboard, and whiteboard-entry helper behavior for context preparation.
- `whiteboard_routing.py` owns the narrow explicit-whiteboard, current-draft edit, and pending-whiteboard carry rules shared by context preparation and orchestration.
- `turn_orchestrator.py` coordinates one `/api/chat` turn across prepared context, Navigator, semantic policy, local actions, normal chat, Scenario Lab, and fallback.
- `local_semantic_actions.py` owns deterministic local save/publish/clarification/experiment action execution once semantic policy has selected that path.
- `turn_payloads.py` owns final backend payload normalization, `system_state`, and `activity`.
- `chat.py` owns the normal answer path: bounded retrieval, protocol candidate injection, vetting, model/fallback response, conservative meta writes, and Memory Trace creation.
- `scenario_lab.py` owns comparative branch generation and persists branch workspaces plus a comparison artifact.
- `semantic_frame.py` and `semantic_policy.py` are transitional read-model/policy layers for product-facing understanding and narrow local actions such as save, publish, and experiment management.

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
- Memory Trace records now carry structured frontmatter metadata such as turn mode, workspace scope, recalled ids, learned ids, and preserved-context ids so retrieval can rank on continuity signals instead of relying only on the transcript body.

## Tests

- [tests/test_repo_hygiene.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_repo_hygiene.py.md)
- [tests/test_context_engine.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_context_engine.py.md)
- [tests/test_context_support.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_context_support.py.md)
- [tests/test_draft_artifact_lifecycle.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_draft_artifact_lifecycle.py.md)
- [tests/test_local_semantic_actions.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_local_semantic_actions.py.md)
- [tests/test_protocol_engine.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_protocol_engine.py.md)
- [tests/test_record_cards.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_record_cards.py.md)
- [tests/test_search.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_search.py.md)
- [tests/test_server.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_server.py.md)
- [tests/test_turn_payloads.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_turn_payloads.py.md)
- [tests/test_whiteboard_routing.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/tests/test_whiteboard_routing.py.md)

## Scripts

- [scripts/check_repo_hygiene.py.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/python/scripts/check_repo_hygiene.py.md)
