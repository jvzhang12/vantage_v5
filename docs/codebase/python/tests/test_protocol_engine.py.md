# `tests/test_protocol_engine.py`

Focused unit tests for the backend Protocol Engine.

## Purpose

- Verify `ProtocolEngine.resolve_for_turn()`, `ProtocolEngine.interpret_and_apply()`, and `ProtocolEngine.build_guidance()` independently from `/api/chat`.
- Lock down the Navigator-control-panel contract, interpreter-driven learning/upsert behavior, and protocol guidance construction before Chat and Scenario Lab consume that guidance.

## Coverage

- Supported `apply_protocol` actions resolve into ordered protocol kinds and action reasons.
- Duplicate protocol kinds are deduplicated.
- Unsupported protocol kinds are ignored with warnings.
- Missing control panels can still produce task-surface protocol guidance for recognizable work types such as email or explicit Scenario Lab, while unrelated turns return an empty protocol result.
- Interpreter-driven protocol updates write a stable protocol record, return an `upsert_protocol` action, and merge the updated record into the turn's concept records when the user explicitly expresses reusable future behavior.
- One-off draft requests can recall a protocol without writing or updating that protocol, even if the interpreter over-eagerly proposes an update.
- Interpreter decisions that only recall a protocol preserve existing concept records without writing.
- Guidance construction prefers persisted/canonical protocol records over built-ins and keeps protocol metadata explicit.
- Guidance construction falls back to built-in protocols, such as Scenario Lab, when no persisted or canonical protocol exists.
