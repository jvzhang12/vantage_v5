# `tests/test_local_semantic_actions.py`

Focused tests for the local semantic-action engine.

## Purpose

- Verify the policy-context facts that let semantic policy safely act on visible whiteboard work.
- Verify ambiguous local actions produce typed clarification turn parts.
- Verify experiment-status local actions produce the expected local turn facts and experiment payload.

## Coverage

- Current visible whiteboard publish requests mark `publish_target_confirmed`.
- Ambiguous save requests return `LocalTurnBodyParts(mode="clarification")`.
- Active experiment status requests return `LocalTurnBodyParts(mode="local_action")` without invoking generic chat.
