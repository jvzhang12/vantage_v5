# `src/vantage_v5/services/protocol_engine.py`

Backend protocol-resolution boundary for one chat turn.

## Purpose

- Convert Navigator `control_panel` protocol actions into a typed `ResolvedTurnProtocols` object.
- Keep protocol action validation deterministic while preserving the target architecture: the Navigator can press `apply_protocol`, and deterministic task-surface loading can also attach recurring protocols such as email, research-paper, or explicit Scenario Lab guidance without another model call.
- Run the protocol interpreter and apply structured protocol upsert decisions only when deterministic write policy says the user is explicitly changing reusable behavior.
- Build protocol guidance candidates for a turn, including persisted protocol overrides and built-in fallback recipes.
- Own protocol API catalog lookup/listing and API-driven protocol updates so `server.py` stays a thin HTTP adapter.
- Give the orchestrator a deeper protocol interface instead of parsing raw control-panel dictionaries directly.

## Key Classes

- `ResolvedProtocolAction`: one validated protocol action, including protocol kind, source, and optional reason.
- `ResolvedTurnProtocols`: immutable turn-level protocol result with `applied_protocol_kinds`, action details, and warnings.
- `ProtocolGuidance`: immutable turn-level protocol guidance with normalized protocol kinds, candidate memory items, and warnings.
- `ProtocolTurnResult`: immutable result for interpreter-driven protocol learning, including the optional `upsert_protocol` action, updated protocol record, recall kinds, merged concept records, and rationale.
- `ProtocolCatalogEntry`: protocol API catalog fact that contains either a persisted protocol record or a built-in protocol kind.
- `ProtocolCatalog`: immutable list of protocol catalog entries for API serialization.
- `ProtocolEngine`: implements `resolve_for_turn(navigation, request, context) -> ResolvedTurnProtocols`, `interpret_and_apply(...) -> ProtocolTurnResult`, `build_guidance(protocol_kinds, concept_records) -> ProtocolGuidance`, `list_catalog(...) -> ProtocolCatalog`, `lookup_catalog_entry(...)`, and `update_from_api(...)`.

## Notable Behavior

- Supports `email`, `research_paper`, and `scenario_lab` through the canonical protocol normalization helper.
- Deduplicates repeated protocol actions while preserving Navigator action order.
- Adds task-surface protocol actions after Navigator actions: email-looking turns load the email protocol, research-paper-looking turns load the research-paper protocol, and explicit Scenario Lab turns load the Scenario Lab protocol.
- Ignores unsupported protocol kinds with warnings instead of letting arbitrary raw strings reach Chat or Scenario Lab.
- `interpret_and_apply()` owns protocol learning/upsert side effects. It only acts on a structured `ProtocolInterpreter` decision after a deterministic reusable-preference/protocol-edit gate passes, writes through `ConceptStore.upsert_protocol()`, returns the `ExecutedAction`, and merges the updated protocol back into the concept records used for the turn.
- Ordinary one-off drafting or revision requests may recall a protocol as guidance, but they do not update the protocol record unless the user explicitly frames the instruction as reusable future behavior.
- `build_guidance()` owns the high-priority protocol candidate construction used by Chat and Scenario Lab, so those services no longer call the lower-level `protocol_candidates_for_kinds()` helper directly.
- `list_catalog()` and `lookup_catalog_entry()` dedupe persisted protocols by protocol kind and add built-ins only when no persisted override exists.
- `update_from_api()` builds the write model and persists a user-editable override through `ConceptStore.upsert_protocol()`, including built-in overrides such as `scenario_lab`.
- Persisted protocol records take precedence over built-ins; if no persisted protocol exists for a built-in kind such as `scenario_lab`, the engine returns the built-in protocol as advisory reasoning guidance.
