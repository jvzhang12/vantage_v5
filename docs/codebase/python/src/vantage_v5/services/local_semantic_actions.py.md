# `src/vantage_v5/services/local_semantic_actions.py`

Deterministic local semantic-action boundary for narrow `/api/chat` actions that should not go through generic model chat.

## Purpose

- Keep local save, publish, clarification, and experiment-status handling out of `server.py`.
- Provide the `SemanticPolicyContext` facts needed by `semantic_policy.py`.
- Convert semantic-policy decisions into typed `TurnResultParts` / `LocalTurnBodyParts` for `turn_payloads.py`.
- Reuse `DraftArtifactLifecycle` for whiteboard save/publish storage work.

## Key Classes / Functions

- `LocalSemanticTurnContext`: typed input for building a local semantic-action result from prepared context, semantic frame/policy payloads, pinned context, and runtime scope.
- `LocalSemanticActionEngine`: service used by `TurnOrchestrator`.
- `policy_context()`: builds the small boolean `SemanticPolicyContext` consumed by `decide_semantic_policy()`.
- `build_turn_parts()`: returns `TurnResultParts` for clarification, local save, local publish, or experiment-management turns; returns `None` for ordinary chat/model turns.
- `session_info()`: returns the experiment state payload needed by turn payload assembly.

## Notable Behavior

- This module does not route broad user intent from raw text. It consumes the already-built semantic frame and semantic-policy decision.
- The only text check here is the narrow confirmation check for whether a visible whiteboard publish request names the current work product.
- Whiteboard save/publish actions delegate persistence and graph-action construction to `DraftArtifactLifecycle`.
- Public response compatibility remains in `turn_payloads.py`; this module only produces local-turn facts.
