# `tests/test_turn_payloads.py`

Focused unit tests for backend turn payload assembly.

## Purpose

- Verify `LocalTurnContext`, `LocalTurnBodyParts`, `TurnResultParts`, Chat/Scenario Lab body parts, turn interpretation assembly, workspace disclosure assembly, and full turn assemblers independently from `/api/chat`.
- Lock down local-action payload compatibility while `turn_payloads.py` grows from a finalizer into a deeper assembler.

## Coverage

- Local action payloads use explicit `LocalTurnBodyParts` before preserving created-record/learned compatibility, graph-action aliases, pinned-context aliases, typed turn interpretation, safe `system_state`, and completed `activity`.
- Hidden/excluded workspaces remain content-free in local clarification payloads and do not claim grounding context.
- Turn interpretation assembly preserves Navigator control-panel fields, pinned-context compatibility aliases, whiteboard source labels, and Scenario Lab hiding of chat-only whiteboard resolution.
- Workspace turn-payload assembly preserves transient content disclosure, hidden durable content behavior, existing extra fields, and cleaned Scenario Lab metadata.
- Chat body assembly preserves memory aliases, candidate-memory aliases, `recall` / `working_memory`, `recall_details`, learned records, trace records, and created-record compatibility.
- Scenario Lab body assembly preserves memory aliases, default no-op meta action, `graph_action=None`, comparison question aliases, branch list, comparison artifact, recommendation, and created-record compatibility.
- Successful service-turn payloads assemble typed chat/Scenario Lab body parts before preserving turn interpretation, semantic frame/policy, graph-action aliases, created-record compatibility, workspace disclosure, experiment status, safe state, and activity.
- Scenario Lab fallback payloads assemble typed fallback chat body parts before preserving the explicit `scenario_lab.status="failed"` contract, `scenario_lab_error`, pinned-context aliases, workspace disclosure, and activity payload.
