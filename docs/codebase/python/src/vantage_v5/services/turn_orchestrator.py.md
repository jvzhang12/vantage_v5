# `src/vantage_v5/services/turn_orchestrator.py`

Backend orchestration boundary for one chat turn.

## Purpose

- Move the `/api/chat` lifecycle out of the HTTP route and behind a deeper service interface.
- Keep the Navigator-led control-panel architecture centralized: the orchestrator calls the Navigator, validates/executes structured controls through deterministic services, and routes to chat or Scenario Lab.
- Coordinate prepared context, surface invocation, resolved protocols, semantic frame/policy, local semantic actions, Scenario Lab fallback, and final payload assembly without making the route own every internal step.

## Key Classes

- `TurnOrchestratorHooks`: remaining narrow dependency boundary for the Scenario Lab entry threshold.
- `TurnOrchestrator`: owns the behavior-preserving turn lifecycle.

## Notable Behavior

- Context preparation now lives in `context_engine.py`; the orchestrator consumes one `PreparedTurnContext` instead of loading/blanking/overlaying whiteboards and pending drafts itself.
- Protocol action parsing now lives in `protocol_engine.py`; the orchestrator consumes a `ResolvedTurnProtocols` object instead of parsing raw `control_panel` dictionaries itself.
- Surface invocation now lives in `surface_invocation.py`; after Navigator interpretation, the orchestrator asks this deterministic policy whether a domain surface such as whiteboard, calendar day, task focus, or code artifact should be summoned and attaches that explanation to every chat payload.
- Before Attention selection is normalized, the orchestrator gives Navigator's control-plane fallback a chance to add explicit saved/open-material UI intent. This keeps Attention responsible for retrieval/selection while Navigator remains the authority for opening a UI surface.
- Whiteboard routing now lives in `whiteboard_routing.py`; the orchestrator asks `WhiteboardRoutingEngine` to resolve the final whiteboard mode and explicit draft-request flag instead of receiving those behaviors as hooks.
- Local semantic-action handling now lives in `local_semantic_actions.py`; the orchestrator asks that service for semantic-policy context, local save/publish/clarification/experiment turn parts, and experiment payloads.
- Successful chat and Scenario Lab service-turn post-processing now lives in `turn_payloads.py`; the orchestrator hands typed service `to_body_parts()` output through `ServiceTurnPayloadParts` after the selected service returns, instead of passing prebuilt public payload dictionaries.
- When a service turn writes a low-level JSON trace, the orchestrator carries that trace path forward on an internal payload key so the HTTP boundary can append final-response observability after server-side post-processing.
- Turn interpretation shaping and workspace disclosure now live in `turn_payloads.py`; the orchestrator creates one typed `TurnInterpretationParts` object and passes it through local, service, and Scenario Lab fallback assembler paths.
- Scenario Lab fallback response shaping now lives in `turn_payloads.py`; the orchestrator still performs the fallback chat call, then hands typed fallback chat body parts plus sanitized failure metadata to the assembler so raw provider or exception text does not become chat-card copy.
- Local semantic-policy actions now return `TurnResultParts`; the orchestrator attaches the shared typed interpretation parts and sends them through `assemble_local_turn_payload()` so local actions use the same assembler boundary as other turn outcomes.
- This extraction still intentionally uses a callback for the Scenario Lab entry threshold. That keeps the refactor safe while creating deeper interfaces incrementally.
- Scenario Lab failures still fall back to normal chat and preserve the same explicit failure payload, but the user-facing error message is now generic and retry-oriented rather than the raw exception string.
- Local semantic-policy actions can still short-circuit the turn before model response generation.
- Durable work-product requests can now override an interpreter `chat` or `offer` whiteboard mode into `draft` through `surface_invocation`, while explicit composer `chat`, `offer`, and `draft` modes still win.
- The orchestrator now builds a narrowed TurnPlan surface-authority view after surface invocation and attention-selection normalization. Open-only, close, and preserve surface behavior is applied from that TurnPlan view rather than from independent downstream predicate checks.
- Final Navigator-selected `open_only` Whiteboard invocations force chat execution and pass an explicit auto-graph-write suppression flag into chat, even when the earlier base route looked drafty, so opening selected saved material cannot accidentally create a workspace draft, graph action, concept, or artifact record. Explicit Whiteboard draft requests and active visible-Whiteboard edit follow-ups can still restore draft execution through the existing Whiteboard routing guards instead of being mislabeled as open-only context.
- Visible-surface close actions short-circuit as local chat acknowledgements before ChatService, Scenario Lab, meta writes, artifact mutation compilation, or workspace drafting. They preserve the visible surface's saved data and only ask the frontend to remove the current surface from view/context.
- Preserve-visible-surface turns stay in normal chat while suppressing automatic graph writes and downstream surface replacement, so keep/leave-open commands remain no-op UI preservation rather than fresh calendar/task/whiteboard opens.
- Later phases can decide whether the Scenario Lab entry threshold should become a policy object, but the broad whiteboard and local semantic-action hooks have moved behind deeper services.
