# `src/vantage_v5/services/turn_payloads.py`

Final response payload assembly helpers for chat, local actions, and Scenario Lab turns.

## Purpose

- Keep `/api/chat` response compatibility in one backend module instead of spreading compatibility aliases through route code.
- Normalize `created_record` / `learned`, graph-action ids, and whiteboard update `type` / `status` aliases.
- Attach pinned-context and selected-record compatibility fields.
- Attach safe `system_state` and final-turn `activity` payloads without leaking hidden draft content.
- Sanitize public Memory Trace DTOs, Memory Trace-derived candidate rows, Attention state, and vetting ids at the payload boundary so `/api/chat` can expose bounded aliases without raw trace bodies, prompt text, or prompt-derived storage ids.

## Key Classes / Functions

- `LocalTurnBodyParts`: typed fact object for the local semantic-action body: assistant message, local mode, optional graph action, created record, and workspace update.
- `TurnResultParts`: typed local-turn envelope around `LocalTurnBodyParts`, prepared context, semantic frame/policy, pinned context, experiment state, and optional turn interpretation.
- `LocalTurnContext`: shared local-turn context object used by server-side semantic-policy actions before the assembler creates `TurnResultParts`.
- `TurnInterpretationParts`: typed input object for the Navigator/whiteboard interpretation envelope.
- `ChatTurnBodyParts`: typed input object for the normal chat service-turn body that `ChatTurn.to_body_parts()` exposes and `ChatTurn.to_dict()` delegates to.
- `ScenarioLabTurnBodyParts`: typed input object for the Scenario Lab service-turn body that `ScenarioLabTurn.to_body_parts()` exposes and `ScenarioLabTurn.to_dict()` delegates to.
- `assemble_turn_interpretation_payload()`: builds the public `turn_interpretation` shape, including pinned-context compatibility aliases and whiteboard mode source.
- `build_local_turn_parts()`: builds `TurnResultParts` from `LocalTurnContext`, an explicit action-specific `LocalTurnBodyParts`, optional workspace override, and typed turn interpretation.
- `assemble_chat_turn_body()`: builds the normal chat payload body, including `memory` / `selected_memory`, `recall` / `working_memory`, `turn_vault_notes`, `recall_details`, learned records, trace record, optional protocol-write authority metadata, and created-record compatibility.
- `assemble_scenario_lab_turn_body()`: builds the Scenario Lab payload body, including grouped memory aliases, comparison artifact, branch list, default no-op meta action, and `scenario_lab` summary object.
- `assemble_workspace_payload_for_turn()`: merges service-returned workspace payloads with the authoritative workspace document while preserving transient-content disclosure and scenario metadata.
- `assemble_local_turn_payload()`: builds local-action and clarification payloads from `TurnResultParts`.
- `ServiceTurnPayloadParts`: typed input object for successful service turns returned by normal chat or Scenario Lab. It accepts typed service body parts, not a prebuilt public payload dictionary.
- `assemble_service_turn_payload()`: assembles the typed service body, then applies successful service-turn post-processing: pinned aliases, turn interpretation, semantic frame/policy, workspace disclosure, experiment status, safe state, and activity.
- `ScenarioLabFallbackParts`: typed input object for the explicit Scenario Lab failure/fallback payload. It also accepts typed fallback chat body parts instead of a prebuilt public payload dictionary.
- `assemble_scenario_lab_fallback_payload()`: builds the existing Scenario Lab failure payload after the orchestrator falls back to normal chat.
- `finalize_turn_payload()`: normalizes the final mutable payload shape before safe state is attached.
- `turn_stage`, `stage_progress`, and `stage_audit`: optional staging fields accepted by typed turn body/envelope parts and normalized through `turn_staging.py` helpers when present.
- `attach_safe_turn_state()`: appends `system_state` and `activity`.
- `safe_system_state_payload()`: creates a redacted system self-description for the turn.
- `safe_activity_payload()`: creates completed activity steps for Inspect and quiet activity copy.

## Notable Behavior

- `system_state.workspace.has_visible_content` is boolean only; hidden draft body content is not exposed through system state.
- Public Memory Trace records and Memory Trace-derived candidate rows are reduced to safe views: the current-turn record uses the `current-turn` alias, selected/recalled prior-turn records use bounded `memory_trace:prior-turn-N` aliases, and raw `body` / `content` / storage ids stay out of the browser payload.
- Public attention-selection ids that point at Memory Trace storage are also rewritten to safe prior-turn aliases before they enter the response envelope.
- Public Attention state reattachment and vetting payloads reuse the same aliasing so late server post-processing cannot reintroduce raw Memory Trace ids or content.
- `system_state.available_controls` includes the Navigator/control-panel surface controls, including non-destructive `close_surface` and no-op `preserve_surface`.
- `activity.steps` and `activity.items` intentionally mirror each other during the compatibility window.
- This module preserves legacy `selected_record` and `working_memory`-adjacent payload expectations while the product language continues moving toward pinned context and Recall.
- The assembler-deepening slices moved local semantic-action payload construction, normal Chat and Scenario Lab service-turn body construction, successful service-turn post-processing, Scenario Lab fallback payload construction, typed turn interpretation shaping, and workspace turn-payload disclosure here while keeping the lower-level finalizer wrappers available as compatibility helpers.
- Local, service, and Scenario Lab fallback paths can now pass `TurnInterpretationParts`; the assembler converts it to the public dictionary shape consistently for every turn outcome.
- `ChatTurn.to_dict()` and `ScenarioLabTurn.to_dict()` remain compatibility methods, but the orchestrator now passes their typed `to_body_parts()` output into `ServiceTurnPayloadParts` / `ScenarioLabFallbackParts`, so those public response assemblers no longer accept raw `turn_payload` dictionaries.
- Local semantic actions now mirror that pattern: action handlers explicitly produce `LocalTurnBodyParts`, `build_local_turn_parts()` wraps those facts in the prepared local context, and `assemble_local_turn_payload()` owns the public local-action / clarification DTO aliases.
- Staging payloads are backward-compatible and optional. Existing callers can omit them, while Navigator-as-stager orchestration can pass typed `TurnStage`, `StageProgressEvent`, and `StageAuditResult` objects or already-shaped dictionaries for preservation in the final response.
- `surface_invocation` is now preserved across local, successful service, and Scenario Lab fallback payload paths. It appears top-level, in redacted `system_state`, and as a safe activity step when a non-chat surface is selected, so Inspect can explain why Vantage summoned whiteboard/calendar/task/code surfaces.
- Additive `surface_action` payloads derived from `surface_invocation` are preserved top-level, mirrored into safe system state, and summarized in activity so client-applied state changes such as closing visible surfaces are traceable without implying writes.
