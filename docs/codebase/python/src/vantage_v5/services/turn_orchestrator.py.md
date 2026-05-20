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
- The orchestrator now builds a narrowed TurnPlan surface-authority view after surface invocation, attention-selection normalization, semantic policy, and turn-interpretation assembly, passing request-level write hints such as `memory_intent` into that policy. Open-only, close, preserve, and structured visible/selected-artifact Q&A no-write behavior is applied from that TurnPlan view rather than from independent downstream predicate checks.
- Final Navigator-selected `open_only` Whiteboard invocations force chat execution and pass TurnPlan-derived auto-graph-write plus protocol-write suppression into chat, even when the earlier base route looked drafty, so opening selected saved material cannot accidentally create a workspace draft, graph action, concept, protocol write, or artifact record. Explicit Whiteboard draft requests and active visible-Whiteboard edit follow-ups can still restore draft execution through the existing Whiteboard routing guards instead of being mislabeled as open-only context.
- Hard TurnPlan no-write surface authority also gates local semantic `artifact_save` and `artifact_publish` actions before they can assemble local write payloads. Clarification and non-write local actions still use the existing semantic-policy path.
- The orchestrator now builds TurnPlan draft authority before normal chat execution and passes that verdict into `ChatService.reply()`. Pending Whiteboard offers/drafts are allowed only when structured draft/offer authority exists; open-only, close, preserve, and artifact-Q&A no-write turns force chat/no-draft execution. If hard no-write denies a structured draft/offer candidate, including one carried as suppressed preserve metadata, the orchestrator returns a small local no-draft/no-offer receipt before model prose can imply a Whiteboard update happened.
- Local semantic `artifact_save` / `artifact_publish` candidates now also pass through the TurnPlan artifact-write authority gate before `LocalSemanticActionEngine.build_turn_parts()` can assemble or persist a save/publish result. The gate allows only structured artifact write intent with an available workspace target and no hard no-write surface authority; storage and persistence still use the existing local semantic action implementation.
- When a hard no-write surface action denies a mixed save/publish request, the orchestrator returns a small local receipt that reflects the actual outcome instead of asking the chat model to describe a write that did not happen.
- The orchestrator passes finalized surface invocation, turn interpretation, and semantic policy context into `ChatService.reply()` so the chat path can apply the TurnPlan memory-write authority gate before executing meta-produced `create_memory` candidates.
- Structured memory intent from request-level `memory_intent="remember"`, Navigator/control-panel `remember`, or semantic-policy memory actions is resolved before chat execution. That effective memory intent lets explicit remember turns reach the existing meta memory path while hard no-write surface authority still suppresses memory candidates.
- Reminder-shaped task capture commands such as “remember to create slides tomorrow” are treated as operational task proposals rather than durable memory writes when the request itself did not carry explicit `memory_intent="remember"`. The orchestrator reuses the artifact-action task-capture fallback as a validation signal and removes conflicting control-panel memory actions before surface invocation and ChatService execution.
- When a caller supplies an in-scope live whiteboard buffer without a separate `visible_artifacts` entry, the orchestrator adds a compact visible Whiteboard artifact view for routing/model context. This keeps structured close/preserve actions and save/publish target validation aligned with the API-visible whiteboard without persisting or changing the workspace.
- Mixed hard no-write surface actions plus structured concept-write intent return a local receipt that reflects the actual outcome, for example preserving or closing the visible Whiteboard while saying that no concept was learned.
- Visible-surface close actions short-circuit as local chat acknowledgements before ChatService, Scenario Lab, meta writes, artifact mutation compilation, or workspace drafting. They preserve the visible surface's saved data and only ask the frontend to remove the current surface from view/context.
- Preserve-visible-surface turns stay in normal chat while suppressing automatic graph writes and downstream surface replacement, so keep/leave-open commands remain no-op UI preservation rather than fresh calendar/task/whiteboard opens.
- Later phases can decide whether the Scenario Lab entry threshold should become a policy object, but the broad whiteboard and local semantic-action hooks have moved behind deeper services.
