# `src/vantage_v5/services/protocols.py`

Uses an LLM interpreter to turn user requests into structured protocol decisions, then turns those decisions into deterministic protocol writes or high-priority Recall candidates.

## Purpose

- Interpret whether a turn should update a reusable protocol, recall an existing protocol, both, or neither.
- Store protocol guidance as stable `type: protocol` concept records rather than duplicate one-off memories.
- Accept structured variables such as email signature, style, and format preferences from the interpreter.
- Force interpreter-selected protocols into Recall for later draft requests so chat can follow the user's preferred workflow.
- Provide a built-in Scenario Lab protocol for first-principles, counterfactual, causal, tradeoff, and assumption-surfacing guidance.
- Convert Navigator `apply_protocol` control-panel actions into protocol kinds the deterministic layer can load.

## Core Data Flow

- `ProtocolInterpreter.interpret()` calls the model with the current user message, recent chat, supported protocol kinds (`email`, `research_paper`, and `scenario_lab`), and existing protocol records. It returns a `ProtocolInterpretation` containing an optional `ProtocolWrite` and protocol kinds to recall. `ProtocolEngine` owns calling this interpreter during a turn.
- `build_protocol_write_from_interpretation()` merges interpreter-provided variables with existing protocol variables and default scaffolding, then returns a `ProtocolWrite` payload that `ProtocolEngine` can persist through `ConceptStore.upsert_protocol()`.
- `build_protocol_write_from_update()` builds the same persisted protocol shape from the explicit Inspect editor API, preserving existing variables when the update omits them and marking built-in overrides when a built-in kind is customized.
- `protocol_candidates_for_kinds()` receives protocol kinds selected by the interpreter or Navigator, then returns matching protocol records as high-score `CandidateMemory` objects with protocol editor metadata. If no saved record exists for a built-in kind such as `scenario_lab`, it creates a virtual protocol candidate marked as built-in and modifiable so Inspect can offer a custom override.
- `protocol_kinds_from_control_panel()` scans Navigator actions for `apply_protocol` and returns supported protocol kinds for execution.
- `find_protocol_record()`, `normalize_protocol_kind()`, and `built_in_protocol_kind_for_lookup()` support protocol API lookup by id or kind.
- Protocol bodies are plain Markdown with a `Protocol`, `Variables`, `Procedure`, and `Latest Instruction` section so they remain inspectable in the concept store.

## Notable Edge Cases

- Protocol updates are intentionally interpreter-driven: deterministic code does not parse keywords or names to decide whether a request is reusable.
- Explicit protocol editor updates are user-directed API writes, separate from interpreter-driven learning.
- Navigator-applied protocols are still LLM-directed: deterministic code only reads the structured `apply_protocol` action and validates the requested kind.
- If no model client is configured, protocol interpretation returns no action rather than falling back to brittle keyword classification.
- Deterministic code only executes the structured decision returned by the interpreter.
