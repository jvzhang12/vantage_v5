# Deep Module Refactor Plan

## Summary

This refactor makes Vantage easier to evolve by turning broad, leaky coordination code into deeper modules with smaller interfaces. The first implementation slice focused on the backend chat-turn path: extract a `TurnOrchestrator`, a `ContextEngine`, a `ProtocolEngine`, and a payload assembly boundary while preserving the existing `/api/chat` response contract.

The goal is not to rename everything or redesign behavior. The goal is to make fewer places know about the full turn lifecycle.

## North Star

The intended shape is:

```text
/api/chat
  -> TurnOrchestrator.run(request, session)
      -> Context Engine
      -> Navigator
      -> Protocol Engine
      -> Chat or Scenario Lab
      -> Draft/Artifact Lifecycle for local save/publish actions
      -> Turn Payload Assembler
  -> TurnResult payload
```

The route should eventually know only HTTP concerns: request validation, auth/session lookup, and returning the result. It should not know every step required to interpret intent, resolve context, route Scenario Lab, attach safe system state, or keep compatibility aliases alive.

## Phase 1: Turn Orchestrator

Create `src/vantage_v5/services/turn_orchestrator.py`.

The first version owned the `/api/chat` lifecycle:

- call the Navigator when a navigation decision was not provided
- resolve whiteboard mode
- collect applied protocol kinds from the Navigator control panel
- build semantic frame and semantic policy
- short-circuit local semantic actions
- route to Scenario Lab or normal chat
- fall back to normal chat if Scenario Lab fails
- hand final payload assembly to the payload assembler

The first pass accepted server-specific callbacks for storage helpers and policy-local actions. Phase 2 moved context callbacks into `ContextEngine`, and the local semantic-action pass moved policy-local actions into `LocalSemanticActionEngine`, leaving the orchestrator focused on interpretation, policy, routing, fallback, and payload assembly.

## Phase 2: Context Engine

Create `src/vantage_v5/services/context_engine.py`.

The Context Engine owns context preparation before Navigator routing:

- resolve experiment session and runtime
- resolve active or requested whiteboard id
- normalize whiteboard context scope
- load, blank, or overlay the whiteboard document
- resolve pinned context
- normalize, carry, force-carry, or drop pending whiteboard state
- compute whiteboard entry mode
- build the small continuity frame for Navigator
- return one `PreparedTurnContext`

This phase is now implemented with `prepare_turn_context(request_context) -> PreparedTurnContext`. Pure workspace scope, live-buffer, redaction, pending-whiteboard, and entry-mode helper behavior now lives in `ContextSupport`; pinned-context summaries, whiteboard source summaries, and Navigator continuity frames now live in `ContextSourceResolver`. `ContextEngineHooks` is reduced to runtime selection plus method references from those context collaborators.

## Phase 2.5: Whiteboard Routing And Context Support

Create `src/vantage_v5/services/whiteboard_routing.py` and `src/vantage_v5/services/context_support.py`.

This slice owns the remaining narrow whiteboard/context helper behavior:

- resolve final whiteboard mode from UI request, Navigator decision, explicit whiteboard phrasing, and current-draft edit continuity
- detect explicit whiteboard draft/open requests for turn interpretation
- normalize workspace scope for live buffers and explicit whiteboard requests
- build live-buffer and unsaved-buffer `WorkspaceDocument` values without persisting them
- redact hidden whiteboard content while preserving workspace identity and scenario metadata
- normalize pending whiteboard `type` / `status` aliases
- carry or drop pending whiteboard state using the existing narrow follow-up rules
- compute whiteboard entry mode

This phase is now implemented. `TurnOrchestrator` depends on `WhiteboardRoutingEngine` instead of whiteboard-routing hooks, and `ContextEngine` depends on `ContextSupport` instead of many storage-shaped helper callbacks.

## Phase 3: Turn Payload Assembler

Create `src/vantage_v5/services/turn_payloads.py`.

The assembler owns final response shaping:

- maintain `created_record` / `learned` compatibility
- normalize graph-action record ids
- normalize whiteboard `type` / `status` aliases
- attach pinned and selected context fields
- attach safe `system_state`
- attach final-turn `activity`
- avoid exposing hidden draft content through `system_state`

This module should be reusable by normal chat, Scenario Lab fallback, and local semantic actions.

Assembler deepening is now well underway: `LocalTurnContext`, `LocalTurnBodyParts`, and `TurnResultParts` exist, local semantic-action / clarification helpers now explicitly produce typed local body facts, `ChatTurn.to_dict()` and `ScenarioLabTurn.to_dict()` delegate service-turn body construction to typed assembler parts, successful chat / successful Scenario Lab service-turn post-processing lives there through `assemble_service_turn_payload()`, Scenario Lab fallback response construction lives there through `assemble_scenario_lab_fallback_payload()`, and typed turn-interpretation plus workspace-disclosure envelopes now live there too. `ServiceTurnPayloadParts` and `ScenarioLabFallbackParts` now accept typed service body parts rather than prebuilt public `turn_payload` dictionaries, so the assembler is the single deep boundary for service-turn DTO construction. Local actions follow the same pattern: `TurnResultParts` is now an envelope around `LocalTurnBodyParts`, not a shape that resembles the public response DTO.

## Phase 3.5: Local Semantic Action Engine

Create `src/vantage_v5/services/local_semantic_actions.py`.

This slice owns deterministic local action execution after semantic policy has selected a narrow local path:

- build the `SemanticPolicyContext` facts used by `semantic_policy.py`
- clarify ambiguous save/publish/inspectable local actions
- save visible whiteboard snapshots through `DraftArtifactLifecycle`
- publish visible whiteboards through `DraftArtifactLifecycle`
- answer experiment-status / exit-intent turns locally
- return typed `TurnResultParts` / `LocalTurnBodyParts` instead of public response dictionaries

This phase is now implemented. `TurnOrchestrator` depends on `LocalSemanticActionEngine` directly instead of broad `semantic_policy_context` and `semantic_policy_local_parts` hooks, and `server.py` no longer owns local semantic-action execution.

## Phase 4: Protocol Engine

Create `src/vantage_v5/services/protocol_engine.py`.

The Protocol Engine owns protocol action resolution for a turn:

- consume Navigator `control_panel` protocol actions
- validate supported protocol kinds
- deduplicate repeated `apply_protocol` actions while preserving Navigator order
- expose a typed `ResolvedTurnProtocols` object
- keep unsupported protocol actions from reaching Chat or Scenario Lab
- preserve Navigator-as-control-panel architecture

This phase is now implemented as a stronger protocol boundary. Chat and Scenario Lab still receive `applied_protocol_kinds` for compatibility, but `ProtocolEngine` now owns interpreter-driven protocol learning/upserts, protocol candidate construction, protocol API catalog/list/lookup/update semantics, persisted override precedence, built-in fallback, and the turn guidance DTO used by those services.

## Phase 5: Draft/Artifact Lifecycle

Create `src/vantage_v5/services/draft_artifact_lifecycle.py`.

This slice owns save/publish/whiteboard-promotion behavior:

- save visible whiteboard snapshots
- publish/promote whiteboards into artifacts
- distinguish transient drafts, saved whiteboards, whiteboard snapshots, promoted artifacts, and Scenario Lab comparison hubs
- centralize graph-action, artifact, workspace, and assistant-message result construction for save/publish/promote flows
- preserve experiment-vs-durable write scope
- keep local semantic policy and HTTP routes as thin callers

This phase is now implemented for local semantic save/publish, `/api/workspace` save snapshots, `/api/concepts/promote` whiteboard promotion, `/api/concepts/open` saved-item reopen, and artifact lifecycle card enrichment without changing response contracts. A later pass can decide whether full saved-note card serialization should move behind the same lifecycle boundary.

## Phase 6: Record/Card Presentation

Create `src/vantage_v5/services/record_cards.py`.

This slice owns UI-facing card DTOs for records without taking over storage or lifecycle decisions:

- concept and protocol cards
- built-in protocol cards
- saved memory and artifact cards
- vault/reference note cards
- lineage view fields
- Scenario Lab scenario metadata card fields
- grouped memory payload counts

This phase is now implemented for the server-facing serializers that had been clustered in `server.py`. `DraftArtifactLifecycle` still owns artifact lifecycle enrichment, while `record_cards.py` owns the broader presentation shape and `server.py` imports those helpers instead of hand-building the card DTOs inline.

## Interface Targets

Initial backend interfaces:

```python
context = context_engine.prepare_turn_context(request_context)
payload = orchestrator.run(ChatTurnRequestContext(...))
payload = assembler.finalize(payload, pinned_context_id=..., pinned_context=...)
payload = assembler.attach_safe_turn_state(payload)
```

Later phases can deepen this further:

```python
context = context_engine.prepare(...)
protocols = protocol_engine.resolve_for_turn(...)
artifact = draft_artifact_lifecycle.save_or_publish(...)
payload = turn_payload_assembler.assemble_local_turn_payload(TurnResultParts(...))
payload = turn_payload_assembler.assemble_service_turn_payload(ServiceTurnPayloadParts(...))
payload = turn_payload_assembler.assemble(TurnResultParts(...))
```

## Guardrails

- Do not add broad deterministic raw-text intent sorting.
- Preserve `/api/chat` payload compatibility.
- Preserve Navigator-as-control-panel architecture.
- Keep Scenario Lab behavior unchanged except through tests.
- Keep local semantic actions and confirmation behavior unchanged.
- Update mirrored docs for every new or changed source file.
- Run focused tests after each slice and full backend tests before completion.

## Acceptance Checks

- `/api/chat` still passes normal chat, Scenario Lab, Scenario Lab failure, local save/publish/experiment, draft, and pending-draft tests.
- `system_state` and `activity` payloads remain present and safe.
- Existing frontend normalization tests pass unchanged or with explicit expected-contract updates.
- `python3 scripts/check_repo_hygiene.py` passes.
- `git diff --check` passes.
