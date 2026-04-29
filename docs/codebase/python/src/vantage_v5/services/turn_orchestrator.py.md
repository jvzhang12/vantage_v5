# `src/vantage_v5/services/turn_orchestrator.py`

Backend orchestration boundary for one chat turn.

## Purpose

- Move the `/api/chat` lifecycle out of the HTTP route and behind a deeper service interface.
- Keep the Navigator-led control-panel architecture centralized: the orchestrator calls the Navigator, validates/executes structured controls through deterministic services, and routes to chat or Scenario Lab.
- Coordinate prepared context, resolved protocols, semantic frame/policy, local semantic actions, Scenario Lab fallback, and final payload assembly without making the route own every internal step.

## Key Classes

- `TurnOrchestratorHooks`: remaining narrow dependency boundary for the Scenario Lab entry threshold.
- `TurnOrchestrator`: owns the behavior-preserving turn lifecycle.

## Notable Behavior

- Context preparation now lives in `context_engine.py`; the orchestrator consumes one `PreparedTurnContext` instead of loading/blanking/overlaying whiteboards and pending drafts itself.
- Protocol action parsing now lives in `protocol_engine.py`; the orchestrator consumes a `ResolvedTurnProtocols` object instead of parsing raw `control_panel` dictionaries itself.
- Whiteboard routing now lives in `whiteboard_routing.py`; the orchestrator asks `WhiteboardRoutingEngine` to resolve the final whiteboard mode and explicit draft-request flag instead of receiving those behaviors as hooks.
- Local semantic-action handling now lives in `local_semantic_actions.py`; the orchestrator asks that service for semantic-policy context, local save/publish/clarification/experiment turn parts, and experiment payloads.
- Successful chat and Scenario Lab service-turn post-processing now lives in `turn_payloads.py`; the orchestrator hands typed service `to_body_parts()` output through `ServiceTurnPayloadParts` after the selected service returns, instead of passing prebuilt public payload dictionaries.
- Turn interpretation shaping and workspace disclosure now live in `turn_payloads.py`; the orchestrator creates one typed `TurnInterpretationParts` object and passes it through local, service, and Scenario Lab fallback assembler paths.
- Scenario Lab fallback response shaping now lives in `turn_payloads.py`; the orchestrator still performs the fallback chat call, then hands typed fallback chat body parts plus sanitized failure metadata to the assembler so raw provider or exception text does not become chat-card copy.
- Local semantic-policy actions now return `TurnResultParts`; the orchestrator attaches the shared typed interpretation parts and sends them through `assemble_local_turn_payload()` so local actions use the same assembler boundary as other turn outcomes.
- This extraction still intentionally uses a callback for the Scenario Lab entry threshold. That keeps the refactor safe while creating deeper interfaces incrementally.
- Scenario Lab failures still fall back to normal chat and preserve the same explicit failure payload, but the user-facing error message is now generic and retry-oriented rather than the raw exception string.
- Local semantic-policy actions can still short-circuit the turn before model response generation.
- Later phases can decide whether the Scenario Lab entry threshold should become a policy object, but the broad whiteboard and local semantic-action hooks have moved behind deeper services.
