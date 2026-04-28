# `tests/test_protocol_engine.py`

Focused unit tests for the backend Protocol Engine.

## Purpose

- Verify `ProtocolEngine.resolve_for_turn()`, `ProtocolEngine.interpret_and_apply()`, and `ProtocolEngine.build_guidance()` independently from `/api/chat`.
- Lock down the Navigator-control-panel contract, interpreter-driven learning/upsert behavior, and protocol guidance construction before Chat and Scenario Lab consume that guidance.

## Coverage

- Supported `apply_protocol` actions resolve into ordered protocol kinds and action reasons.
- Duplicate protocol kinds are deduplicated.
- Unsupported protocol kinds are ignored with warnings.
- Missing control panels return an empty protocol result.
- Interpreter-driven protocol updates write a stable protocol record, return an `upsert_protocol` action, and merge the updated record into the turn's concept records.
- Interpreter decisions that only recall a protocol preserve existing concept records without writing.
- Guidance construction prefers persisted protocol overrides over built-ins.
- Guidance construction falls back to built-in protocols, such as Scenario Lab, when no persisted protocol exists.
